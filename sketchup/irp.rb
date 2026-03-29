# IRP — Interior Render Pipeline v1.1
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
require 'digest/sha2'

module IRP
  VERSION = '1.1'
  RESOLUTION = [1920, 1080]
  
  @role_map = {}
  @export_scene = nil  # Locked scene for export
  
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
  # SCENE CONTROL
  # ============================================
  
  def self.current_scene_name
    page = model.pages.selected_page
    page ? page.name : 'Default'
  end
  
  def self.switch_to_scene(name)
    page = model.pages.find { |p| p.name == name }
    if page
      model.pages.selected_page = page
      view.refresh
      sleep(0.3)
      true
    else
      puts "  ⚠ Scene '#{name}' not found"
      false
    end
  end
  
  def self.lock_scene
    @export_scene = current_scene_name
    puts "  🔒 Locked to scene: #{@export_scene}"
  end
  
  def self.verify_scene
    current = current_scene_name
    if @export_scene && current != @export_scene
      puts "  ⚠ Scene changed! Expected: #{@export_scene}, Got: #{current}"
      puts "  ⚠ Switching back..."
      switch_to_scene(@export_scene)
    end
    true
  end
  
  # ============================================
  # EXTRACT — Phase 0
  # ============================================
  
  def self.extract
    dir = skp_dir
    return unless dir
    
    puts ""
    puts "╔══════════════════════════════════════════════════╗"
    puts "║   IRP EXTRACT v#{VERSION}                             ║"
    puts "╚══════════════════════════════════════════════════╝"
    puts ""
    puts "Current scene: #{current_scene_name}"
    puts ""
    
    lock_scene
    
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
      
      # 2. Beauty render from locked scene
      puts ""
      puts "=== BEAUTY RENDER ==="
      verify_scene
      saved_render = save_rendering_options
      setup_normal_rendering
      view.refresh
      sleep(0.3)
      export_image(File.join(temp_dir, 'beauty.png'))
      restore_rendering_options(saved_render)
      puts "  ✓ beauty.png"
      
      # 3. Create zip
      zip_path = File.join(dir, "irp_extract.zip")
      FileUtils.rm_f(zip_path)
      create_zip(temp_dir, zip_path)
      
      puts ""
      puts "╔══════════════════════════════════════════════════╗"
      puts "║   EXTRACT COMPLETE                               ║"
      puts "╚══════════════════════════════════════════════════╝"
      puts ""
      puts "Scene: #{@export_scene}"
      puts "Output: #{zip_path}"
      puts ""
      puts "Next steps:"
      puts "1. Send zip + ТЗ.md to AI for role mapping"
      puts "2. Save role_map.json to: #{dir}"
      puts "3. Run IRP.export (same scene will be used)"
      
    ensure
      FileUtils.rm_rf(temp_dir)
    end
  end
  
  # ============================================
  # EXPORT — Phase 2
  # ============================================
  
  def self.export
    dir = skp_dir
    return unless dir
    
    puts ""
    puts "╔══════════════════════════════════════════════════╗"
    puts "║   IRP EXPORT v#{VERSION}                              ║"
    puts "╚══════════════════════════════════════════════════╝"
    puts ""
    
    # Scene control
    if @export_scene
      puts "Using locked scene: #{@export_scene}"
      switch_to_scene(@export_scene)
    else
      lock_scene
    end
    puts ""
    
    # Load role_map
    role_map_path = File.join(dir, 'role_map.json')
    unless File.exist?(role_map_path)
      puts "ERROR: role_map.json not found!"
      puts "Expected at: #{role_map_path}"
      puts ""
      puts "Run IRP.extract first, then create role_map.json"
      return
    end
    
    load_role_map(role_map_path)
    puts "Loaded role_map.json (#{@role_map.length} entities)"
    puts ""
    
    # Load technical spec if exists
    tz_path = File.join(dir, 'TZ.md')
    tz_path = File.join(dir, 'ТЗ.md') unless File.exist?(tz_path)
    @technical_spec = load_technical_spec(tz_path)
    
    # Create temp folder
    temp_dir = File.join(dir, "irp_bundle_temp")
    FileUtils.rm_rf(temp_dir)
    FileUtils.mkdir_p(temp_dir)
    FileUtils.mkdir_p(File.join(temp_dir, 'masks'))
    FileUtils.mkdir_p(File.join(temp_dir, 'model'))
    
    begin
      # 1. Beauty render
      puts "=== BEAUTY ==="
      verify_scene
      saved_render = save_rendering_options
      setup_normal_rendering
      view.refresh
      sleep(0.3)
      export_image(File.join(temp_dir, 'beauty.png'))
      restore_rendering_options(saved_render)
      puts "  ✓ beauty.png"
      
      # 2. Depth map
      puts ""
      puts "=== DEPTH MAP ==="
      verify_scene
      export_depth_map(temp_dir)
      
      # 3. Boundary mask (binary)
      puts ""
      puts "=== BOUNDARY MASK ==="
      verify_scene
      export_boundary_mask(temp_dir)
      
      # 4. Individual masks
      puts ""
      puts "=== MASKS ==="
      verify_scene
      @role_map.each do |pid, info|
        if export_mask(pid, info[:name], temp_dir)
          puts "  ✓ #{info[:name]}.png"
        else
          puts "  ✗ #{info[:name]}.png (not found)"
        end
      end
      
      # 5. Copy technical spec
      if @technical_spec[:exists]
        FileUtils.cp(@technical_spec[:path], File.join(temp_dir, 'technical_spec.md'))
        puts ""
        puts "=== TECHNICAL SPEC ==="
        puts "  ✓ technical_spec.md (#{@technical_spec[:hash][0..15]}...)"
      end
      
      # 6. Manifest
      puts ""
      puts "=== MANIFEST ==="
      generate_manifest(temp_dir)
      puts "  ✓ manifest.json"
      
      # 7. Blender exports
      puts ""
      puts "=== MODEL EXPORTS ==="
      name_entities_for_export
      export_models(temp_dir)
      revert_structural_changes
      
      # 8. Create zip
      zip_path = File.join(dir, "irp_bundle.zip")
      FileUtils.rm_f(zip_path)
      create_zip(temp_dir, zip_path)
      
      puts ""
      puts "╔══════════════════════════════════════════════════╗"
      puts "║   EXPORT COMPLETE                                ║"
      puts "╚══════════════════════════════════════════════════╝"
      puts ""
      puts "Scene: #{@export_scene}"
      puts "Output: #{zip_path}"
      puts ""
      puts "Bundle contents:"
      puts "  - beauty.png"
      puts "  - depth.png (SketchUp ground truth)"
      puts "  - boundary_mask.png (binary)"
      puts "  - masks/*.png (#{@role_map.length} entities)"
      puts "  - manifest.json (v#{VERSION})"
      puts "  - technical_spec.md" if @technical_spec[:exists]
      puts "  - model.dae/fbx/glb"
      
    ensure
      FileUtils.rm_rf(temp_dir)
    end
  end
  
  # ============================================
  # TECHNICAL SPEC
  # ============================================
  
  def self.load_technical_spec(path)
    if File.exist?(path)
      content = File.read(path, encoding: 'UTF-8')
      hash = Digest::SHA256.hexdigest(content)
      
      # Extract summary (first non-empty line after #)
      summary = content.lines.find { |l| l.start_with?('#') }
      summary = summary ? summary.gsub(/^#+\s*/, '').strip : ''
      
      {
        exists: true,
        path: path,
        hash: "sha256:#{hash}",
        summary: summary
      }
    else
      puts "  ⚠ Technical spec (ТЗ.md) not found"
      { exists: false, path: nil, hash: nil, summary: nil }
    end
  end
  
  # ============================================
  # ROLE MAP
  # ============================================
  
  def self.load_role_map(path)
    data = JSON.parse(File.read(path), symbolize_names: true)
    @role_map = {}
    
    data[:entities].each do |entity|
      @role_map[entity[:pid]] = {
        name: entity[:name],
        role: entity[:role],
        entity_class: entity[:class],
        surface_kind: entity[:surface_kind],
        prompt: entity[:prompt],
        prompt_source: entity[:prompt_source] || "role_map.json",
        reference: entity[:reference],
        critical: entity[:critical] || false
      }
    end
    
    # Track excluded
    @excluded = data[:excluded] || []
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
      
      # Hide ALL entities first
      model.entities.each { |e| e.visible = false if e.respond_to?(:visible=) }
      
      # Show and paint ONLY mapped entities in pure white
      white = Sketchup::Color.new(255, 255, 255)
      @role_map.each do |pid, info|
        entity = find_by_pid(pid)
        if entity
          entity.visible = true
          paint_entity_solid(entity, white)
        end
      end
      
      view.refresh
      sleep(0.2)
      export_image(path)
      
    ensure
      model.abort_operation
    end
    
    puts "  ✓ boundary_mask.png (binary)"
  end
  
  # ============================================
  # INDIVIDUAL MASKS
  # ============================================
  
  def self.export_mask(pid, name, output_dir)
    entity = find_by_pid(pid)
    return false unless entity
    
    path = File.join(output_dir, 'masks', "#{name}.png")
    
    model.start_operation("Export Mask #{name}", true)
    
    begin
      setup_mask_rendering
      hide_all
      
      entity.visible = true
      white = Sketchup::Color.new(255, 255, 255)
      paint_entity_solid(entity, white)
      
      view.refresh
      sleep(0.2)
      export_image(path)
      
    ensure
      model.abort_operation
    end
    
    # Calculate coverage
    coverage = calculate_coverage(path)
    @role_map[pid][:coverage_pct] = coverage
    
    true
  end
  
  def self.calculate_coverage(path)
    # Simple coverage estimation based on file size ratio
    # More accurate would need image processing
    file_size = File.size(path) rescue 0
    max_size = 500000  # Approximate max for full white
    pct = (file_size.to_f / max_size * 100).round(1)
    pct.clamp(0.1, 99.0)
  end
  
  # ============================================
  # PAINTING
  # ============================================
  
  def self.paint_entity_solid(entity, color)
    return unless entity
    paint_recursive_solid(entity, color)
  end
  
  def self.paint_recursive_solid(entity, color)
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
        paint_recursive_solid(e, color)
      end
    end
  end
  
  # ============================================
  # MANIFEST
  # ============================================
  
  def self.generate_manifest(output_dir)
    page = model.pages.selected_page
    camera = view.camera
    
    entities = @role_map.map do |pid, info|
      entity_class = info[:entity_class] || 'fixture'
      
      # Weight by class
      weight = case entity_class
        when 'surface' then 0.55
        when 'fixture' then 0.50
        when 'opening' then 0.0
        else 0.50
      end
      
      # Render mode by class
      render_mode = entity_class == 'opening' ? 'structural_controlnet' : 'regional_ipadapter'
      
      {
        pid: pid,
        name: info[:name],
        role: info[:role],
        class: entity_class,
        surface_kind: info[:surface_kind],
        mask: "masks/#{info[:name]}.png",
        coverage_pct: info[:coverage_pct] || 0.0,
        reference: info[:reference],
        prompt: info[:prompt],
        prompt_source: info[:prompt_source] || "role_map.json",
        critical: info[:critical] || false,
        render_mode: render_mode,
        ipadapter_weight: weight
      }
    end
    
    # Build scene_id from model name and scene
    model_name = File.basename(model.path, '.skp').gsub(/[^a-zA-Z0-9_-]/, '_')
    scene_name = (page ? page.name : 'default').gsub(/[^a-zA-Z0-9_-]/, '_')
    scene_id = "#{model_name}_#{scene_name}"
    
    manifest = {
      version: VERSION,
      scene_id: scene_id,
      created: Time.now.utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
      base_image: 'beauty.png',
      depth_map: 'depth.png',
      boundary_mask: 'boundary_mask.png',
      image_size: {
        width: RESOLUTION[0],
        height: RESOLUTION[1]
      },
      camera: {
        eye: camera.eye.to_a.map { |v| v.to_m.round(3) },
        target: camera.target.to_a.map { |v| v.to_m.round(3) },
        up: camera.up.to_a,
        fov: camera.fov.round(1)
      },
      technical_spec: @technical_spec[:exists] ? {
        path: 'technical_spec.md',
        hash: @technical_spec[:hash],
        summary: @technical_spec[:summary]
      } : nil,
      entities: entities,
      excluded: @excluded
    }
    
    # Remove nil technical_spec
    manifest.delete(:technical_spec) unless manifest[:technical_spec]
    
    File.write(File.join(output_dir, 'manifest.json'), JSON.pretty_generate(manifest))
  end
  
  # ============================================
  # SCENE GRAPH
  # ============================================
  
  def self.build_scene_graph
    page = model.pages.selected_page
    camera = view.camera
    
    # Collect all scenes
    scenes = model.pages.to_a.map do |p|
      cam = p.camera
      {
        name: p.name,
        camera: {
          eye: cam.eye.to_a,
          target: cam.target.to_a,
          up: cam.up.to_a,
          fov: cam.fov
        }
      }
    end
    
    {
      version: VERSION,
      model_name: File.basename(model.path, '.skp'),
      resolution: RESOLUTION,
      current_scene: page ? page.name : 'Default',
      scenes: scenes,
      entities: collect_entities_recursive(model.entities, 0)
    }
  end
  
  def self.collect_entities_recursive(entities, depth)
    result = []
    entities.each do |e|
      next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
      next if e.hidden?
      
      inner = e.is_a?(Sketchup::Group) ? e.entities : e.definition.entities
      face_count = inner.grep(Sketchup::Face).length
      child_count = inner.grep(Sketchup::Group).length + inner.grep(Sketchup::ComponentInstance).length
      
      bounds = e.bounds
      
      result << {
        pid: e.persistent_id,
        name: e.name.empty? ? nil : e.name,
        type: e.class.name.split('::').last,
        depth: depth,
        face_count: face_count,
        child_count: child_count,
        bounds: {
          width: bounds.width.to_m.round(1),
          height: bounds.height.to_m.round(1),
          depth: bounds.depth.to_m.round(1)
        },
        position: [
          bounds.center.x.to_m.round(3),
          bounds.center.y.to_m.round(3),
          bounds.center.z.to_m.round(3)
        ]
      }
      
      # Recurse
      result += collect_entities_recursive(inner, depth + 1)
    end
    result
  end
  
  # ============================================
  # BLENDER EXPORTS
  # ============================================
  
  def self.name_entities_for_export
    @role_map.each do |pid, info|
      entity = find_by_pid(pid)
      if entity
        entity.name = "IRP_#{info[:name]}"
      end
    end
    puts "  Named #{@role_map.length} entities with IRP_ prefix"
  end
  
  def self.export_models(output_dir)
    # DAE (includes camera)
    dae_path = File.join(output_dir, 'model.dae')
    model.export(dae_path, false)
    puts "  ✓ model.dae"
    
    # FBX
    begin
      fbx_path = File.join(output_dir, 'model.fbx')
      model.export(fbx_path, false)
      puts "  ✓ model.fbx"
    rescue => e
      puts "  ✗ model.fbx (#{e.message})"
    end
    
    # GLB
    begin
      glb_path = File.join(output_dir, 'model.glb')
      model.export(glb_path, false)
      puts "  ✓ model.glb"
    rescue => e
      puts "  ✗ model.glb (#{e.message})"
    end
  end
  
  def self.revert_structural_changes
    # Names are reverted with abort_operation in export_mask
  end
  
  # ============================================
  # HELPERS
  # ============================================
  
  def self.find_by_pid(pid)
    model.find_entity_by_persistent_id(pid)
  end
  
  def self.hide_all
    model.entities.each { |e| e.visible = false if e.respond_to?(:visible=) }
  end
  
  def self.show_all_mapped
    hide_all
    @role_map.each do |pid, _|
      entity = find_by_pid(pid)
      entity.visible = true if entity
    end
  end
  
  def self.setup_mask_rendering
    ro = model.rendering_options
    safe_set(ro, 'EdgeDisplayMode', 0)
    safe_set(ro, 'DrawSilhouettes', false)
    safe_set(ro, 'DrawSky', false)
    safe_set(ro, 'DrawGround', false)
    safe_set(ro, 'DisplayFog', false)
    safe_set(ro, 'DisplaySectionPlanes', false)
    safe_set(ro, 'BackgroundColor', Sketchup::Color.new(0, 0, 0))
  end
  
  def self.setup_normal_rendering
    ro = model.rendering_options
    safe_set(ro, 'EdgeDisplayMode', 1)
    safe_set(ro, 'DrawSilhouettes', true)
    safe_set(ro, 'DrawSky', true)
    safe_set(ro, 'DrawGround', true)
  end
  
  def self.safe_set(ro, key, value)
    ro[key] = value
  rescue ArgumentError => e
    puts "  Warning: #{key} not supported, skipping"
  end
  
  def self.save_rendering_options
    ro = model.rendering_options
    {
      'EdgeDisplayMode' => (ro['EdgeDisplayMode'] rescue nil),
      'DrawSilhouettes' => (ro['DrawSilhouettes'] rescue nil),
      'DrawSky' => (ro['DrawSky'] rescue nil),
      'DrawGround' => (ro['DrawGround'] rescue nil),
      'BackgroundColor' => (ro['BackgroundColor'] rescue nil)
    }
  end
  
  def self.restore_rendering_options(saved)
    ro = model.rendering_options
    saved.each do |key, value|
      safe_set(ro, key, value) if value
    end
  end
  
  def self.export_image(path, opts = {})
    options = {
      filename: path,
      width: RESOLUTION[0],
      height: RESOLUTION[1],
      antialias: true,
      transparent: false
    }
    view.write_image(options)
  end
  
  def self.create_zip(source_dir, zip_path)
    require 'rubygems/package'
    require 'zlib'
    
    # Use system zip if available
    if system("zip -r \"#{zip_path}\" . > NUL 2>&1", chdir: source_dir)
      return
    end
    
    # Fallback: manual zip via PowerShell on Windows
    if Sketchup.platform == :platform_win
      cmd = "powershell -Command \"Compress-Archive -Path '#{source_dir}\\*' -DestinationPath '#{zip_path}' -Force\""
      system(cmd)
    end
  end
end

puts ""
puts "IRP v#{IRP::VERSION} loaded. Commands:"
puts "  IRP.extract  — Generate scene_graph + beauty (Phase 0)"
puts "  IRP.export   — Generate masks + depth + models (Phase 2)"
puts ""
puts "Current scene: #{IRP.current_scene_name}"
puts ""
