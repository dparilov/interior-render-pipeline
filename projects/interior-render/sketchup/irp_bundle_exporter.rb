# IRP Scene Bundle Exporter v1
# Interior Render Pipeline - SketchUp Plugin
#
# Экспортирует bundle для рендера:
# - beauty.png (полная сцена)
# - surfaces_only.png (только surfaces)
# - fixtures_only.png (только fixtures)  
# - masks/*.png (бинарные маски каждого entity)
# - manifest.json (метаданные)
#
# Usage:
#   load 'C:/Users/paril/Desktop/irp_bundle_exporter.rb'
#   IRP.extract          # показать scene graph
#   IRP.annotate         # записать роли в модель
#   IRP.export_bundle    # экспортировать bundle
#   IRP.verify           # проверить файлы

require 'sketchup'
require 'json'
require 'fileutils'

module IRP
  # ============================================
  # КОНФИГУРАЦИЯ
  # ============================================
  
  DICT = 'irp'  # название attribute dictionary
  OUTPUT_DIR = 'C:/Users/paril/Downloads/AAAAAAAb'
  EXPORT_WIDTH = 1920
  EXPORT_HEIGHT = 1080
  SCENE_NAME = 'Сцена №1'
  
  # Semantic roles mapping (PID → role)
  # Заполняется один раз, потом хранится в модели
  ROLE_MAP = {
    # Surfaces
    36696 => { role: 'surface.walls', class: 'surface', reference: 'wall_tiles.png', prompt: 'white glossy wavy subway tiles, Costa Nova style, 3D relief texture' },
    36828 => { role: 'surface.floor', class: 'surface', reference: 'floor_tiles.jpg', prompt: 'blue patterned ceramic floor tiles, Equipe Rivoli style' },
    
    # Fixtures
    43754 => { role: 'fixture.bathtub', class: 'fixture', reference: 'bathtub.jpg', prompt: 'white modern freestanding bathtub' },
    359764 => { role: 'fixture.window', class: 'fixture', reference: nil, prompt: 'white PVC window frame with glass' },
    143585 => { role: 'fixture.shower', class: 'fixture', reference: 'shower.jpg', prompt: 'chrome shower fixtures, polished metal' },
    229917 => { role: 'fixture.rainshower', class: 'fixture', reference: 'shower.jpg', prompt: 'chrome rain shower head' },
    352872 => { role: 'fixture.towel_warmer', class: 'fixture', reference: 'towel_warmer.jpg', prompt: 'white heated towel rail' },
    124416 => { role: 'fixture.vanity', class: 'fixture', reference: 'vanity.jpg', prompt: 'dark gray bathroom vanity cabinet with white sink' },
    471300 => { role: 'fixture.mirror', class: 'fixture', reference: 'mirror.jpg', prompt: 'round bathroom mirror with LED backlight' },
    424271 => { role: 'fixture.basket', class: 'fixture', reference: 'basket.jpg', prompt: 'natural wicker laundry basket' }
  }
  
  # ============================================
  # CORE API
  # ============================================
  
  def self.model
    Sketchup.active_model
  end

  def self.view
    model.active_view
  end

  def self.find_by_pid(pid)
    # SketchUp 2017+ has find_entity_by_persistent_id
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

  def self.activate_scene
    page = model.pages[SCENE_NAME]
    if page
      model.pages.selected_page = page
      view.refresh
      sleep(0.3)
      true
    else
      puts "⚠️  Scene '#{SCENE_NAME}' not found!"
      false
    end
  end

  # ============================================
  # EXTRACT - Scene Graph Analysis
  # ============================================

  def self.extract
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   IRP SCENE GRAPH EXTRACTION             ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    registry = []
    walk_entities(model.entities, nil, registry)
    
    puts "Found #{registry.length} groups/components:"
    puts ""
    
    registry.each do |row|
      role_info = ROLE_MAP[row[:pid]]
      if role_info
        puts "  ✓ PID=#{row[:pid]} → #{role_info[:role]}"
      else
        puts "  ? PID=#{row[:pid]} name='#{row[:name]}' (not mapped)"
      end
    end
    
    puts ""
    puts "Mapped: #{ROLE_MAP.keys.count { |pid| find_by_pid(pid) }}/#{ROLE_MAP.length}"
    
    registry
  end

  def self.walk_entities(entities, parent_pid, out)
    entities.each do |e|
      next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
      
      name = if e.is_a?(Sketchup::Group)
        e.name.to_s.empty? ? nil : e.name
      else
        e.definition.name
      end
      
      out << {
        pid: e.persistent_id,
        name: name,
        parent_pid: parent_pid,
        layer: e.layer&.name,
        material: e.material&.display_name,
        type: e.class.to_s.split('::').last
      }
      
      child_entities = e.is_a?(Sketchup::Group) ? e.entities : e.definition.entities
      walk_entities(child_entities, e.persistent_id, out)
    end
  end

  # ============================================
  # ANNOTATE - Write Roles to Model
  # ============================================

  def self.annotate
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   ANNOTATING MODEL WITH ROLES            ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    model.start_operation('IRP Annotate', true)
    
    count = 0
    ROLE_MAP.each do |pid, info|
      entity = find_by_pid(pid)
      unless entity && entity.valid?
        puts "  ⚠️  PID=#{pid} not found"
        next
      end
      
      entity.set_attribute(DICT, 'role', info[:role])
      entity.set_attribute(DICT, 'class', info[:class])
      entity.set_attribute(DICT, 'reference', info[:reference])
      entity.set_attribute(DICT, 'prompt', info[:prompt])
      entity.set_attribute(DICT, 'critical', true)
      
      puts "  ✓ #{info[:role]} (PID=#{pid})"
      count += 1
    end
    
    model.commit_operation
    
    puts ""
    puts "Annotated #{count} entities."
    puts "Attributes stored in '#{DICT}' dictionary."
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

  def self.hide_entity(pid)
    entity = find_by_pid(pid)
    entity.visible = false if entity && entity.respond_to?(:visible=)
  end

  def self.show_entity(pid)
    entity = find_by_pid(pid)
    entity.visible = true if entity && entity.respond_to?(:visible=)
  end

  def self.hide_all_mapped
    ROLE_MAP.keys.each { |pid| hide_entity(pid) }
  end

  def self.show_all_mapped
    ROLE_MAP.keys.each { |pid| show_entity(pid) }
  end

  # ============================================
  # RENDERING OPTIONS
  # ============================================

  def self.save_rendering_options
    rendering = model.rendering_options
    {
      'BackgroundColor' => rendering['BackgroundColor'],
      'DrawHorizon' => rendering['DrawHorizon'],
      'DrawGround' => rendering['DrawGround'],
      'RenderMode' => rendering['RenderMode'],
      'EdgeDisplayMode' => rendering['EdgeDisplayMode'],
      'DrawSilhouettes' => rendering['DrawSilhouettes']
    }
  end

  def self.restore_rendering_options(saved)
    rendering = model.rendering_options
    saved.each do |key, value|
      rendering[key] = value rescue nil
    end
  end

  def self.setup_mask_rendering
    rendering = model.rendering_options
    rendering['BackgroundColor'] = Sketchup::Color.new(0, 0, 0)
    rendering['DrawHorizon'] = false
    rendering['DrawGround'] = false
    rendering['EdgeDisplayMode'] = 0
    rendering['DrawSilhouettes'] = false
    
    # Try to set monochrome-like rendering
    # RenderMode: 0=wireframe, 1=hidden line, 2=shaded, 3=shaded+textures, 4=monochrome
    begin
      rendering['RenderMode'] = 4  # Monochrome in some versions
    rescue
      rendering['RenderMode'] = 2  # Fallback to shaded
    end
  end

  def self.setup_normal_rendering
    rendering = model.rendering_options
    rendering['RenderMode'] = 2  # Shaded with Textures
  end

  # ============================================
  # EXPORT FUNCTIONS
  # ============================================

  def self.export_image(filename, transparent: false)
    options = {
      filename: filename,
      width: EXPORT_WIDTH,
      height: EXPORT_HEIGHT,
      antialias: true,
      transparent: transparent
    }
    view.write_image(options)
  end

  def self.export_beauty
    path = File.join(OUTPUT_DIR, 'beauty.png')
    activate_scene
    setup_normal_rendering
    show_all_mapped
    view.refresh
    export_image(path)
    puts "  ✓ beauty.png"
  end

  def self.export_surfaces_only
    path = File.join(OUTPUT_DIR, 'surfaces_only.png')
    saved = save_visibility
    
    begin
      activate_scene
      setup_normal_rendering
      
      # Show only surfaces
      hide_all_mapped
      ROLE_MAP.each do |pid, info|
        show_entity(pid) if info[:class] == 'surface'
      end
      
      view.refresh
      export_image(path)
      puts "  ✓ surfaces_only.png"
    ensure
      restore_visibility(saved)
    end
  end

  def self.export_fixtures_only
    path = File.join(OUTPUT_DIR, 'fixtures_only.png')
    saved = save_visibility
    
    begin
      activate_scene
      setup_normal_rendering
      
      # Show only fixtures
      hide_all_mapped
      ROLE_MAP.each do |pid, info|
        show_entity(pid) if info[:class] == 'fixture'
      end
      
      view.refresh
      export_image(path, transparent: true)
      puts "  ✓ fixtures_only.png (transparent)"
    ensure
      restore_visibility(saved)
    end
  end

  def self.export_entity_mask(pid, name)
    path = File.join(OUTPUT_DIR, 'masks', "#{name}.png")
    
    saved_vis = save_visibility
    saved_render = save_rendering_options
    
    # Save materials before painting
    entity = find_by_pid(pid)
    saved_materials = save_entity_materials(entity) if entity
    
    begin
      activate_scene
      setup_mask_rendering
      
      # Hide all, show only target entity
      hide_all_mapped
      show_entity(pid)
      
      # Paint entity white for mask
      paint_entity_white(entity) if entity
      
      view.refresh
      sleep(0.3)
      export_image(path)
      
    ensure
      # Restore everything
      restore_entity_materials(entity, saved_materials) if entity && saved_materials
      restore_visibility(saved_vis)
      restore_rendering_options(saved_render)
    end
  end
  
  # Save all materials from entity recursively
  def self.save_entity_materials(entity)
    materials = {}
    save_materials_recursive(entity, materials)
    materials
  end
  
  def self.save_materials_recursive(entity, materials)
    return unless entity
    
    # Save entity material
    if entity.respond_to?(:material)
      materials[entity.object_id] = {
        material: entity.material,
        type: :entity
      }
    end
    
    # Get child entities
    entities = if entity.is_a?(Sketchup::Group)
      entity.entities
    elsif entity.is_a?(Sketchup::ComponentInstance)
      entity.definition.entities
    else
      return
    end
    
    # Save face materials
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        materials[e.object_id] = {
          material: e.material,
          back_material: e.back_material,
          type: :face
        }
      elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        save_materials_recursive(e, materials)
      end
    end
  end
  
  # Restore materials
  def self.restore_entity_materials(entity, materials)
    restore_materials_recursive(entity, materials)
  end
  
  def self.restore_materials_recursive(entity, materials)
    return unless entity
    
    # Restore entity material
    if entity.respond_to?(:material=) && materials[entity.object_id]
      entity.material = materials[entity.object_id][:material]
    end
    
    # Get child entities
    entities = if entity.is_a?(Sketchup::Group)
      entity.entities
    elsif entity.is_a?(Sketchup::ComponentInstance)
      entity.definition.entities
    else
      return
    end
    
    # Restore face materials
    entities.each do |e|
      if e.is_a?(Sketchup::Face) && materials[e.object_id]
        e.material = materials[e.object_id][:material]
        e.back_material = materials[e.object_id][:back_material]
      elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        restore_materials_recursive(e, materials)
      end
    end
  end
  
  # Paint entity white recursively
  def self.paint_entity_white(entity)
    white = Sketchup::Color.new(255, 255, 255)
    
    entity.material = white if entity.respond_to?(:material=)
    
    entities = if entity.is_a?(Sketchup::Group)
      entity.entities
    elsif entity.is_a?(Sketchup::ComponentInstance)
      entity.definition.entities
    else
      return
    end
    
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        e.material = white
        e.back_material = white
      elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        paint_entity_white(e)
      end
    end
  end

  # ============================================
  # MAIN EXPORT
  # ============================================

  def self.export_bundle
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   IRP BUNDLE EXPORT v1                   ║"
    puts "║   Resolution: #{EXPORT_WIDTH}x#{EXPORT_HEIGHT}                 ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    # Create directories
    FileUtils.mkdir_p(OUTPUT_DIR)
    FileUtils.mkdir_p(File.join(OUTPUT_DIR, 'masks'))
    
    # Save initial state
    initial_vis = save_visibility
    initial_render = save_rendering_options
    
    begin
      # 1. Beauty render
      puts "=== PASSES ==="
      export_beauty
      
      # 2. Surfaces only
      export_surfaces_only
      
      # 3. Fixtures only
      export_fixtures_only
      
      # 4. Individual masks
      puts ""
      puts "=== MASKS ==="
      
      ROLE_MAP.each do |pid, info|
        entity = find_by_pid(pid)
        next unless entity && entity.valid?
        
        name = info[:role].split('.').last  # "surface.walls" → "walls"
        export_entity_mask(pid, name)
        puts "  ✓ masks/#{name}.png"
      end
      
      # 5. Generate manifest
      puts ""
      puts "=== MANIFEST ==="
      generate_manifest
      puts "  ✓ manifest.json"
      
    ensure
      restore_visibility(initial_vis)
      restore_rendering_options(initial_render)
      setup_normal_rendering
    end
    
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   EXPORT COMPLETE                        ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    verify
  end

  def self.generate_manifest
    entities = []
    
    ROLE_MAP.each do |pid, info|
      entity = find_by_pid(pid)
      next unless entity && entity.valid?
      
      name = info[:role].split('.').last
      
      entities << {
        pid: pid,
        name: name,
        role: info[:role],
        class: info[:class],
        mask: "masks/#{name}.png",
        reference: info[:reference] ? "references/#{info[:reference]}" : nil,
        prompt: info[:prompt]
      }
    end
    
    manifest = {
      version: 1,
      scene_name: SCENE_NAME,
      resolution: [EXPORT_WIDTH, EXPORT_HEIGHT],
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

  def self.verify
    puts "=== FILES ==="
    
    files = Dir.glob(File.join(OUTPUT_DIR, '**', '*.{png,json}')).sort
    files.each do |f|
      rel = f.sub(OUTPUT_DIR + '/', '')
      size_kb = File.size(f) / 1024
      puts "  #{rel} (#{size_kb} KB)"
    end
    
    puts ""
    puts "Total: #{files.length} files"
  end

end

# ============================================
# STARTUP
# ============================================

puts ""
puts "╔══════════════════════════════════════════╗"
puts "║   IRP Bundle Exporter v1 loaded!         ║"
puts "╚══════════════════════════════════════════╝"
puts ""
puts "Commands:"
puts "  IRP.extract        # show scene graph"
puts "  IRP.annotate       # write roles to model"
puts "  IRP.export_bundle  # export full bundle"
puts "  IRP.verify         # check exported files"
puts ""
puts "Output: #{IRP::OUTPUT_DIR}"
