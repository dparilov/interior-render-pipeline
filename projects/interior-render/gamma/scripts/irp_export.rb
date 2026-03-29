# IRP Export — Phase 2: Mask Export with Role Map
# 
# Экспортирует маски по готовому role_map.json
#
# Usage:
#   load 'C:/path/to/irp_export.rb'
#   IRP.load_map('C:/path/to/role_map.json')
#   IRP.export

require 'sketchup'
require 'json'
require 'fileutils'

module IRP
  OUTPUT_DIR = File.join(ENV['USERPROFILE'] || ENV['HOME'], 'Downloads', 'irp_bundle')
  RESOLUTION = [1920, 1080]
  DICT = 'irp'
  
  @role_map = {}
  
  def self.model
    Sketchup.active_model
  end
  
  def self.view
    model.active_view
  end
  
  # ============================================
  # ROLE MAP LOADING
  # ============================================
  
  def self.load_map(path)
    unless File.exist?(path)
      puts "Error: #{path} not found"
      return false
    end
    
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
    
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   ROLE MAP LOADED                        ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    @role_map.each do |pid, info|
      entity = find_by_pid(pid)
      status = entity ? "✓" : "✗"
      puts "  #{status} [#{pid}] #{info[:name]} (#{info[:role]})"
    end
    
    puts ""
    puts "Total: #{@role_map.length} entities"
    
    true
  end
  
  def self.role_map
    @role_map
  end
  
  # ============================================
  # ENTITY LOOKUP
  # ============================================
  
  def self.find_by_pid(pid)
    if model.respond_to?(:find_entity_by_persistent_id)
      model.find_entity_by_persistent_id(pid)
    else
      find_by_pid_recursive(model.entities, pid)
    end
  end
  
  def self.find_by_pid_recursive(entities, pid)
    entities.each do |e|
      return e if e.respond_to?(:persistent_id) && e.persistent_id == pid
      if e.is_a?(Sketchup::Group)
        result = find_by_pid_recursive(e.entities, pid)
        return result if result
      elsif e.is_a?(Sketchup::ComponentInstance)
        result = find_by_pid_recursive(e.definition.entities, pid)
        return result if result
      end
    end
    nil
  end
  
  # ============================================
  # VISIBILITY MANAGEMENT
  # ============================================
  
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
      entity.visible = false if entity && entity.respond_to?(:visible=)
    end
    view.refresh
  end
  
  def self.show_all_mapped
    @role_map.keys.each do |pid|
      entity = find_by_pid(pid)
      entity.visible = true if entity && entity.respond_to?(:visible=)
    end
    view.refresh
  end
  
  # ============================================
  # RENDERING
  # ============================================
  
  def self.save_rendering_options
    ro = model.rendering_options
    {
      'BackgroundColor' => ro['BackgroundColor'],
      'DrawHorizon' => ro['DrawHorizon'],
      'DrawGround' => ro['DrawGround'],
      'EdgeDisplayMode' => ro['EdgeDisplayMode'],
      'DrawSilhouettes' => ro['DrawSilhouettes']
    }
  end
  
  def self.restore_rendering_options(saved)
    ro = model.rendering_options
    saved.each { |k, v| ro[k] = v rescue nil }
  end
  
  def self.setup_mask_rendering
    ro = model.rendering_options
    ro['BackgroundColor'] = Sketchup::Color.new(0, 0, 0)
    ro['DrawHorizon'] = false
    ro['DrawGround'] = false
    ro['EdgeDisplayMode'] = 0
    ro['DrawSilhouettes'] = false
  end
  
  def self.setup_normal_rendering
    ro = model.rendering_options
    ro['DrawHorizon'] = true
    ro['DrawGround'] = true
  end
  
  def self.export_image(path, transparent: false)
    options = {
      filename: path,
      width: RESOLUTION[0],
      height: RESOLUTION[1],
      antialias: true,
      transparent: transparent
    }
    view.write_image(options)
  end
  
  # ============================================
  # MASK EXPORT
  # ============================================
  
  def self.paint_entity_white(entity)
    white = Sketchup::Color.new(255, 255, 255)
    paint_recursive(entity, white)
  end
  
  def self.paint_recursive(entity, color)
    entity.material = color if entity.respond_to?(:material=)
    
    entities = if entity.is_a?(Sketchup::Group)
      entity.entities
    elsif entity.is_a?(Sketchup::ComponentInstance)
      entity.definition.entities
    else
      return
    end
    
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        e.material = color
        e.back_material = color
      elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        paint_recursive(e, color)
      end
    end
  end
  
  def self.export_mask(pid, name)
    entity = find_by_pid(pid)
    return false unless entity && entity.valid?
    
    path = File.join(OUTPUT_DIR, 'masks', "#{name}.png")
    
    # Use operation for undo
    model.start_operation('Export Mask', true)
    
    begin
      saved_vis = save_visibility
      saved_render = save_rendering_options
      
      setup_mask_rendering
      hide_all_mapped
      
      # Show and paint target
      entity.visible = true
      paint_entity_white(entity)
      
      view.refresh
      sleep(0.2)
      
      export_image(path)
      
    ensure
      model.abort_operation  # Undo paint changes
      restore_visibility(saved_vis)
      restore_rendering_options(saved_render)
    end
    
    true
  end
  
  # ============================================
  # MAIN EXPORT
  # ============================================
  
  def self.export
    if @role_map.empty?
      puts "Error: No role map loaded. Run IRP.load_map('path/to/role_map.json') first."
      return
    end
    
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   IRP EXPORT — Phase 2                   ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    FileUtils.mkdir_p(OUTPUT_DIR)
    FileUtils.mkdir_p(File.join(OUTPUT_DIR, 'masks'))
    
    saved_vis = save_visibility
    saved_render = save_rendering_options
    
    begin
      # 1. Beauty
      puts "=== PASSES ==="
      setup_normal_rendering
      show_all_mapped
      view.refresh
      export_image(File.join(OUTPUT_DIR, 'beauty.png'))
      puts "  ✓ beauty.png"
      
      # 2. Surfaces only
      hide_all_mapped
      @role_map.each do |pid, info|
        entity = find_by_pid(pid)
        entity.visible = true if entity && info[:entity_class] == 'surface'
      end
      view.refresh
      export_image(File.join(OUTPUT_DIR, 'surfaces_only.png'))
      puts "  ✓ surfaces_only.png"
      
      # 3. Fixtures only
      hide_all_mapped
      @role_map.each do |pid, info|
        entity = find_by_pid(pid)
        entity.visible = true if entity && info[:entity_class] == 'fixture'
      end
      view.refresh
      export_image(File.join(OUTPUT_DIR, 'fixtures_only.png'), transparent: true)
      puts "  ✓ fixtures_only.png"
      
      # 4. Individual masks
      puts ""
      puts "=== MASKS ==="
      @role_map.each do |pid, info|
        if export_mask(pid, info[:name])
          puts "  ✓ #{info[:name]}.png"
        else
          puts "  ✗ #{info[:name]}.png (entity not found)"
        end
      end
      
      # 5. Manifest
      puts ""
      puts "=== MANIFEST ==="
      generate_manifest
      puts "  ✓ manifest.json"
      
      # 6. Name entities for Blender (IRP_walls, IRP_floor, etc.)
      puts ""
      puts "=== NAMING FOR BLENDER ==="
      name_entities_for_export
      
      # 7. Blender exports
      puts ""
      puts "=== BLENDER EXPORTS ==="
      export_dae
      export_fbx
      export_glb
      
    ensure
      restore_visibility(saved_vis)
      restore_rendering_options(saved_render)
    end
    
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   EXPORT COMPLETE                        ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    puts "Output: #{OUTPUT_DIR}"
    
    list_files
  end
  
  def self.generate_manifest
    entities = []
    
    @role_map.each do |pid, info|
      entities << {
        pid: pid,
        name: info[:name],
        role: info[:role],
        class: info[:entity_class],
        mask: "masks/#{info[:name]}.png",
        reference: info[:reference],
        prompt: info[:prompt]
      }
    end
    
    page = model.pages.selected_page
    
    manifest = {
      version: 1,
      scene_name: page ? page.name : 'Default',
      resolution: RESOLUTION,
      images: {
        beauty: 'beauty.png',
        surfaces_only: 'surfaces_only.png',
        fixtures_only: 'fixtures_only.png'
      },
      entities: entities
    }
    
    path = File.join(OUTPUT_DIR, 'manifest.json')
    File.write(path, JSON.pretty_generate(manifest))
  end
  
  def self.list_files
    puts ""
    puts "=== FILES ==="
    Dir.glob(File.join(OUTPUT_DIR, '**', '*')).sort.each do |f|
      next if File.directory?(f)
      rel = f.sub(OUTPUT_DIR + '/', '')
      size_kb = File.size(f) / 1024
      puts "  #{rel} (#{size_kb} KB)"
    end
  end
  
  # ============================================
  # BLENDER EXPORTS (DAE + FBX)
  # ============================================
  
  def self.name_entities_for_export
    @role_map.each do |pid, info|
      entity = find_by_pid(pid)
      next unless entity && entity.valid?
      
      irp_name = "IRP_#{info[:name]}"
      
      # Set entity name (survives FBX/GLB export)
      if entity.respond_to?(:name=)
        entity.name = irp_name
        puts "  ✓ PID #{pid} → #{irp_name}"
      end
      
      # For ComponentInstance, also set definition name
      if entity.is_a?(Sketchup::ComponentInstance)
        old_def_name = entity.definition.name
        # Don't rename if it already has a meaningful name
        if old_def_name.nil? || old_def_name.empty? || old_def_name.start_with?('#') || old_def_name.start_with?('Group') || old_def_name.include?('Группа')
          entity.definition.name = irp_name
        end
      end
    end
  end
  
  def self.export_dae
    path = File.join(OUTPUT_DIR, 'model.dae')
    options = {
      triangulated_faces: true,
      doublesided_faces: true,
      texture_maps: true,
      preserve_instancing: true
    }
    
    if model.export(path, options)
      puts "  ✓ model.dae (for camera)"
      true
    else
      puts "  ✗ DAE export failed"
      false
    end
  end
  
  def self.export_fbx
    path = File.join(OUTPUT_DIR, 'model.fbx')
    options = {
      triangulated_faces: true,
      doublesided_faces: true,
      texture_maps: true,
      swap_yz: false,
      units: "m"
    }
    
    if model.export(path, options)
      puts "  ✓ model.fbx (for geometry)"
      true
    else
      puts "  ✗ FBX export failed"
      false
    end
  end
  
  def self.export_glb
    path = File.join(OUTPUT_DIR, 'model.glb')
    options = {}
    
    if model.export(path, options)
      puts "  ✓ model.glb (for Blender)"
      true
    else
      puts "  ✗ GLB export failed"
      false
    end
  end
end

# Startup
puts ""
puts "╔══════════════════════════════════════════╗"
puts "║   IRP Export loaded                      ║"
puts "╚══════════════════════════════════════════╝"
puts ""
puts "Commands:"
puts "  IRP.load_map('C:\\Users\\paril/Downloads/irp_bundle/role_map.json')"
puts "  IRP.export"
puts ""
puts "Output: #{IRP::OUTPUT_DIR}"
puts ""
