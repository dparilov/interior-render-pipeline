# IRP — Interior Render Pipeline
# 
# Single script, two commands:
#   IRP.extract  → irp_extract.zip (scene_graph + beauty)
#   IRP.export   → irp_bundle.zip (masks + depth + boundary + models)
#
# Files are created next to the active .skp file.
# Export requires role_map.json in the same folder.
#
# Usage:
#   load 'http://100.96.1.25:9090/irp.rb'
#   IRP.extract   # First run: generates extract zip for AI mapping
#   # ... put role_map.json next to .skp ...
#   IRP.export    # Second run: generates full bundle

require 'sketchup'
require 'json'
require 'fileutils'

module IRP
  RESOLUTION = [1920, 1080]
  
  @role_map = {}
  
  def self.model
    Sketchup.active_model
  end
  
  def self.view
    model.active_view
  end
  
  def self.skp_dir
    path = model.path
    if path.empty?
      UI.messagebox("Please save the model first.")
      return nil
    end
    File.dirname(path)
  end
  
  def self.timestamp
    Time.now.strftime('%Y%m%d_%H%M')
  end
  
  # ============================================
  # EXTRACT — Phase 0
  # ============================================
  
  def self.extract
    dir = skp_dir
    return unless dir
    
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   IRP EXTRACT                            ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    # Create temp folder
    temp_dir = File.join(dir, "irp_extract_temp")
    FileUtils.rm_rf(temp_dir)
    FileUtils.mkdir_p(temp_dir)
    
    begin
      # 1. Scene graph
      puts "=== SCENE GRAPH ==="
      scene_graph = build_scene_graph
      File.write(File.join(temp_dir, 'scene_graph.json'), JSON.pretty_generate(scene_graph))
      puts "  ✓ scene_graph.json (#{scene_graph[:entities].length} entities)"
      
      # 2. Beauty render
      puts ""
      puts "=== BEAUTY RENDER ==="
      saved_render = save_rendering_options
      setup_normal_rendering
      view.refresh
      sleep(0.3)
      export_image(File.join(temp_dir, 'beauty.png'))
      restore_rendering_options(saved_render)
      puts "  ✓ beauty.png"
      
      # 3. Create zip (overwrite previous)
      zip_path = File.join(dir, "irp_extract.zip")
      FileUtils.rm_f(zip_path)
      create_zip(temp_dir, zip_path)
      
      puts ""
      puts "╔══════════════════════════════════════════╗"
      puts "║   EXTRACT COMPLETE                       ║"
      puts "╚══════════════════════════════════════════╝"
      puts ""
      puts "Output: #{zip_path}"
      puts ""
      puts "Next steps:"
      puts "1. Send zip to AI for role mapping"
      puts "2. Save role_map.json to: #{dir}"
      puts "3. Run IRP.export"
      
    ensure
      FileUtils.rm_rf(temp_dir)
    end
  end
  
  def self.build_scene_graph
    page = model.pages.selected_page
    camera = view.camera
    
    {
      version: 'gamma',
      model_name: File.basename(model.path, '.skp'),
      camera: {
        eye: camera.eye.to_a,
        target: camera.target.to_a,
        up: camera.up.to_a,
        fov: camera.fov
      },
      resolution: RESOLUTION,
      scene_name: page ? page.name : 'Default',
      entities: collect_entities_recursive(model.entities, 0)
    }
  end
  
  def self.collect_entities_recursive(entities, depth, max_depth = 20)
    return [] if depth > max_depth
    
    result = []
    entities.each do |e|
      next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
      next unless e.visible?
      
      bounds = e.bounds
      
      entry = {
        pid: e.persistent_id,
        type: e.is_a?(Sketchup::Group) ? 'Group' : 'ComponentInstance',
        name: e.name.to_s.empty? ? nil : e.name,
        depth: depth,
        bounds: {
          width: bounds.width.to_mm.round(1),
          height: bounds.height.to_mm.round(1),
          depth: bounds.depth.to_mm.round(1)
        },
        position: bounds.center.to_a.map { |v| v.to_m.round(3) }
      }
      
      # Count faces
      inner = e.is_a?(Sketchup::Group) ? e.entities : e.definition.entities
      entry[:face_count] = inner.grep(Sketchup::Face).length
      entry[:child_count] = inner.grep(Sketchup::Group).length + 
                            inner.grep(Sketchup::ComponentInstance).length
      
      result << entry
      
      # Recurse
      children = collect_entities_recursive(inner, depth + 1, max_depth)
      result.concat(children)
    end
    
    result
  end
  
  # ============================================
  # EXPORT — Phase 2
  # ============================================
  
  def self.export
    dir = skp_dir
    return unless dir
    
    role_map_path = File.join(dir, 'role_map.json')
    
    unless File.exist?(role_map_path)
      puts ""
      puts "ERROR: role_map.json not found!"
      puts "Expected: #{role_map_path}"
      puts ""
      puts "Run IRP.extract first, then place role_map.json in the same folder."
      return
    end
    
    load_role_map(role_map_path)
    
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   IRP EXPORT                             ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    puts "Role map: #{@role_map.length} entities"
    puts ""
    
    # Create temp folder
    temp_dir = File.join(dir, "irp_bundle_temp")
    FileUtils.rm_rf(temp_dir)
    FileUtils.mkdir_p(temp_dir)
    FileUtils.mkdir_p(File.join(temp_dir, 'masks'))
    
    saved_vis = save_visibility
    saved_render = save_rendering_options
    
    begin
      # 1. Beauty
      puts "=== PASSES ==="
      setup_normal_rendering
      show_all_mapped
      view.refresh
      export_image(File.join(temp_dir, 'beauty.png'))
      puts "  ✓ beauty.png"
      
      # 2. Depth map (ground truth)
      puts ""
      puts "=== DEPTH MAP ==="
      export_depth_map(temp_dir)
      
      # 3. Boundary mask
      puts ""
      puts "=== BOUNDARY MASK ==="
      export_boundary_mask(temp_dir)
      
      # 4. Individual masks
      puts ""
      puts "=== MASKS ==="
      @role_map.each do |pid, info|
        if export_mask(pid, info[:name], temp_dir)
          puts "  ✓ #{info[:name]}.png"
        else
          puts "  ✗ #{info[:name]}.png (not found)"
        end
      end
      
      # 5. Manifest
      puts ""
      puts "=== MANIFEST ==="
      generate_manifest(temp_dir)
      puts "  ✓ manifest.json"
      
      # 6. Blender exports
      puts ""
      puts "=== BLENDER EXPORTS ==="
      name_entities_for_export
      export_models(temp_dir)
      revert_structural_changes
      
      # 7. Create zip (overwrite previous)
      zip_path = File.join(dir, "irp_bundle.zip")
      FileUtils.rm_f(zip_path)
      create_zip(temp_dir, zip_path)
      
      puts ""
      puts "╔══════════════════════════════════════════╗"
      puts "║   EXPORT COMPLETE                        ║"
      puts "╚══════════════════════════════════════════╝"
      puts ""
      puts "Output: #{zip_path}"
      
    ensure
      FileUtils.rm_rf(temp_dir)
      restore_visibility(saved_vis)
      restore_rendering_options(saved_render)
    end
  end
  
  def self.load_role_map(path)
    data = JSON.parse(File.read(path), symbolize_names: true)
    @role_map = {}
    
    data[:entities].each do |entity|
      @role_map[entity[:pid]] = {
        name: entity[:name],
        role: entity[:role],
        entity_class: entity[:class],
        prompt: entity[:prompt],
        reference: entity[:reference]
      }
    end
  end
  
  # ============================================
  # DEPTH MAP
  # ============================================
  
  def self.export_depth_map(output_dir)
    path = File.join(output_dir, 'depth.png')
    
    model.start_operation('Export Depth', true)
    
    begin
      show_all_mapped
      setup_mask_rendering
      
      # Paint by distance from camera
      camera = view.camera
      eye = camera.eye
      
      # Find depth range
      faces = collect_all_faces
      distances = faces.map { |f| eye.distance(f.bounds.center) }
      min_dist = distances.min || 0
      max_dist = distances.max || 1
      range = max_dist - min_dist
      range = 1.0 if range < 0.001
      
      # Paint faces
      faces.each do |face|
        dist = eye.distance(face.bounds.center)
        normalized = 1.0 - ((dist - min_dist) / range)
        gray = (normalized * 255).to_i.clamp(0, 255)
        color = Sketchup::Color.new(gray, gray, gray)
        face.material = color
        face.back_material = color
      end
      
      view.refresh
      sleep(0.2)
      export_image(path)
      
    ensure
      model.abort_operation
    end
    
    puts "  ✓ depth.png"
  end
  
  def self.collect_all_faces(entities = nil, faces = [])
    entities ||= model.entities
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        faces << e
      elsif e.is_a?(Sketchup::Group) && e.visible?
        collect_all_faces(e.entities, faces)
      elsif e.is_a?(Sketchup::ComponentInstance) && e.visible?
        collect_all_faces(e.definition.entities, faces)
      end
    end
    faces
  end
  
  # ============================================
  # BOUNDARY MASK
  # ============================================
  
  def self.export_boundary_mask(output_dir)
    path = File.join(output_dir, 'boundary_mask.png')
    
    model.start_operation('Export Boundary', true)
    
    begin
      setup_mask_rendering
      show_all_mapped
      
      # Paint everything white
      @role_map.each do |pid, info|
        entity = find_by_pid(pid)
        paint_entity_white(entity) if entity
      end
      
      view.refresh
      sleep(0.2)
      export_image(path)
      
    ensure
      model.abort_operation
    end
    
    puts "  ✓ boundary_mask.png"
  end
  
  # ============================================
  # INDIVIDUAL MASKS
  # ============================================
  
  def self.export_mask(pid, name, output_dir)
    entity = find_by_pid(pid)
    return false unless entity && entity.valid?
    
    path = File.join(output_dir, 'masks', "#{name}.png")
    
    model.start_operation('Export Mask', true)
    
    begin
      setup_mask_rendering
      hide_all_mapped
      
      entity.visible = true
      paint_entity_white(entity)
      
      view.refresh
      sleep(0.2)
      export_image(path)
      
    ensure
      model.abort_operation
    end
    
    true
  end
  
  def self.paint_entity_white(entity)
    return unless entity
    white = Sketchup::Color.new(255, 255, 255)
    paint_recursive(entity, white)
  end
  
  def self.paint_recursive(entity, color)
    entity.material = color if entity.respond_to?(:material=)
    
    inner = if entity.is_a?(Sketchup::Group)
      entity.entities
    elsif entity.is_a?(Sketchup::ComponentInstance)
      entity.definition.entities
    else
      return
    end
    
    inner.each do |e|
      if e.is_a?(Sketchup::Face)
        e.material = color
        e.back_material = color
      elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        paint_recursive(e, color)
      end
    end
  end
  
  # ============================================
  # MANIFEST
  # ============================================
  
  def self.generate_manifest(output_dir)
    page = model.pages.selected_page
    
    entities = @role_map.map do |pid, info|
      {
        pid: pid,
        name: info[:name],
        role: info[:role],
        class: info[:entity_class],
        mask: "masks/#{info[:name]}.png",
        reference: info[:reference],
        prompt: info[:prompt]
      }
    end
    
    manifest = {
      version: '1.0',
      scene_name: page ? page.name : 'Default',
      resolution: RESOLUTION,
      base_image: 'beauty.png',
      depth_map: 'depth.png',
      boundary_mask: 'boundary_mask.png',
      entities: entities
    }
    
    File.write(File.join(output_dir, 'manifest.json'), JSON.pretty_generate(manifest))
  end
  
  # ============================================
  # BLENDER EXPORTS
  # ============================================
  
  def self.name_entities_for_export
    model.start_operation('Name for Export', true)
    
    @role_map.each do |pid, info|
      entity = find_by_pid(pid)
      next unless entity
      
      name = "IRP_#{info[:name]}"
      
      if entity.is_a?(Sketchup::Group)
        # Convert to component for proper export
        comp = entity.to_component
        comp.definition.name = name
        comp.name = name
      else
        entity.definition.name = name
        entity.name = name
      end
    end
    
    # Don't commit — will be reverted
  end
  
  def self.revert_structural_changes
    model.abort_operation
    puts "  ✓ Structural changes reverted"
  end
  
  def self.export_models(output_dir)
    # DAE (for camera)
    dae_path = File.join(output_dir, 'model.dae')
    model.export(dae_path, false)
    puts "  ✓ model.dae"
    
    # FBX
    fbx_path = File.join(output_dir, 'model.fbx')
    if model.export(fbx_path, false)
      puts "  ✓ model.fbx"
    end
    
    # GLB
    glb_path = File.join(output_dir, 'model.glb')
    if model.export(glb_path, false)
      puts "  ✓ model.glb"
    end
  end
  
  # ============================================
  # UTILITIES
  # ============================================
  
  def self.find_by_pid(pid, entities = nil)
    entities ||= model.entities
    entities.each do |e|
      return e if e.respond_to?(:persistent_id) && e.persistent_id == pid
      
      if e.is_a?(Sketchup::Group)
        found = find_by_pid(pid, e.entities)
        return found if found
      elsif e.is_a?(Sketchup::ComponentInstance)
        found = find_by_pid(pid, e.definition.entities)
        return found if found
      end
    end
    nil
  end
  
  def self.save_visibility
    states = {}
    save_visibility_recursive(model.entities, states)
    states
  end
  
  def self.save_visibility_recursive(entities, states)
    entities.each do |e|
      if e.respond_to?(:visible?) && e.respond_to?(:persistent_id)
        states[e.persistent_id] = e.visible?
      end
      if e.is_a?(Sketchup::Group)
        save_visibility_recursive(e.entities, states)
      elsif e.is_a?(Sketchup::ComponentInstance)
        save_visibility_recursive(e.definition.entities, states)
      end
    end
  end
  
  def self.restore_visibility(states)
    restore_visibility_recursive(model.entities, states)
    view.refresh
  end
  
  def self.restore_visibility_recursive(entities, states)
    entities.each do |e|
      if e.respond_to?(:visible=) && e.respond_to?(:persistent_id)
        e.visible = states[e.persistent_id] if states.key?(e.persistent_id)
      end
      if e.is_a?(Sketchup::Group)
        restore_visibility_recursive(e.entities, states)
      elsif e.is_a?(Sketchup::ComponentInstance)
        restore_visibility_recursive(e.definition.entities, states)
      end
    end
  end
  
  def self.hide_all_mapped
    @role_map.keys.each do |pid|
      entity = find_by_pid(pid)
      entity.visible = false if entity
    end
    view.refresh
  end
  
  def self.show_all_mapped
    @role_map.keys.each do |pid|
      entity = find_by_pid(pid)
      entity.visible = true if entity
    end
    view.refresh
  end
  
  def self.save_rendering_options
    ro = model.rendering_options
    {
      edge_mode: ro['EdgeDisplayMode'],
      silhouettes: ro['DrawSilhouettes'],
      profiles: ro['DrawDepthQue'],
      sky: ro['DrawSky'],
      ground: ro['DrawGround'],
      fog: ro['DisplayFog'],
      section_planes: ro['DisplaySectionPlanes']
    }
  end
  
  def self.restore_rendering_options(saved)
    ro = model.rendering_options
    ro['EdgeDisplayMode'] = saved[:edge_mode]
    ro['DrawSilhouettes'] = saved[:silhouettes]
    ro['DrawDepthQue'] = saved[:profiles]
    ro['DrawSky'] = saved[:sky]
    ro['DrawGround'] = saved[:ground]
    ro['DisplayFog'] = saved[:fog]
    ro['DisplaySectionPlanes'] = saved[:section_planes]
  end
  
  def self.setup_normal_rendering
    ro = model.rendering_options
    ro['EdgeDisplayMode'] = 1
    ro['DrawSilhouettes'] = true
    ro['DrawSky'] = false
    ro['DrawGround'] = false
    ro['DisplayFog'] = false
    ro['DisplaySectionPlanes'] = false
  end
  
  def self.setup_mask_rendering
    ro = model.rendering_options
    ro['EdgeDisplayMode'] = 0
    ro['DrawSilhouettes'] = false
    ro['DrawSky'] = false
    ro['DrawGround'] = false
    ro['DisplayFog'] = false
    ro['DisplaySectionPlanes'] = false
    ro['BackgroundColor'] = Sketchup::Color.new(0, 0, 0)
  end
  
  def self.export_image(path, opts = {})
    options = {
      filename: path,
      width: RESOLUTION[0],
      height: RESOLUTION[1],
      antialias: false,
      transparent: opts[:transparent] || false
    }
    view.write_image(options)
  end
  
  def self.create_zip(source_dir, zip_path)
    # Ruby doesn't have built-in zip, use system call
    if Gem.win_platform?
      # Windows: use PowerShell
      ps_cmd = "Compress-Archive -Path '#{source_dir}\\*' -DestinationPath '#{zip_path}' -Force"
      system("powershell -Command \"#{ps_cmd}\"")
    else
      # Unix
      system("cd '#{source_dir}' && zip -r '#{zip_path}' .")
    end
  end
end

puts ""
puts "IRP loaded. Commands:"
puts "  IRP.extract  — Generate scene_graph + beauty (Phase 0)"
puts "  IRP.export   — Generate masks + depth + models (Phase 2)"
puts ""
