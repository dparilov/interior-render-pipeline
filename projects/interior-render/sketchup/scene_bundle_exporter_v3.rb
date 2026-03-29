# Scene Bundle Exporter v3 for SketchUp
# LAYERED APPROACH: Surfaces first, then objects on top
# NO material changes - only visibility toggling
#
# Usage:
#   load 'C:/Users/paril/Desktop/scene_bundle_exporter_v3.rb'
#   SceneBundleExporter.preview
#   SceneBundleExporter.export_bundle

require 'sketchup'
require 'fileutils'

module SceneBundleExporter
  # ============================================
  # КОНФИГУРАЦИЯ
  # ============================================
  OUTPUT_DIR = 'C:/Users/paril/Desktop/bundle'
  EXPORT_WIDTH = 1920
  EXPORT_HEIGHT = 1080
  SCENE_NAME = 'Сцена №1'
  
  # ============================================
  # СТРУКТУРА СЦЕНЫ
  # ============================================
  
  # Surfaces (структурные поверхности) — рендерятся первым проходом
  SURFACES = {
    36696 => 'walls',
    36828 => 'floor'
  }
  
  # Objects (предметы) — добавляются поверх
  OBJECTS = {
    43754 => 'bathtub',
    359764 => 'window',
    143585 => 'shower',
    229917 => 'rainshower',
    352872 => 'towel_warmer',
    124416 => 'vanity',
    471300 => 'mirror',
    424271 => 'basket'
  }
  
  # Все entities
  ALL_ENTITIES = SURFACES.merge(OBJECTS)

  # ============================================
  # УТИЛИТЫ
  # ============================================
  
  def self.model
    Sketchup.active_model
  end

  def self.view
    model.active_view
  end

  def self.find_by_pid(pid)
    find_recursive(model.entities, pid)
  end

  def self.find_recursive(entities, pid)
    entities.each do |e|
      return e if e.respond_to?(:persistent_id) && e.persistent_id == pid
      if e.is_a?(Sketchup::Group)
        result = find_recursive(e.entities, pid)
        return result if result
      elsif e.is_a?(Sketchup::ComponentInstance)
        result = find_recursive(e.definition.entities, pid)
        return result if result
      end
    end
    nil
  end

  def self.activate_scene(name)
    page = model.pages[name]
    if page
      model.pages.selected_page = page
      view.refresh
      sleep(0.2)
      true
    else
      puts "⚠️  Scene '#{name}' not found!"
      false
    end
  end

  # ============================================
  # VISIBILITY MANAGEMENT (без изменения материалов!)
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

  def self.hide_all_known_entities
    ALL_ENTITIES.keys.each do |pid|
      entity = find_by_pid(pid)
      entity.visible = false if entity
    end
  end

  def self.show_entity(pid)
    entity = find_by_pid(pid)
    entity.visible = true if entity
  end

  def self.hide_entity(pid)
    entity = find_by_pid(pid)
    entity.visible = false if entity
  end

  # ============================================
  # EXPORT
  # ============================================

  def self.export_image(filename)
    options = {
      filename: filename,
      width: EXPORT_WIDTH,
      height: EXPORT_HEIGHT,
      antialias: true,
      transparent: false
    }
    view.write_image(options)
  end

  # Экспорт полного скетча (всё видимо)
  def self.export_sketch
    output_path = File.join(OUTPUT_DIR, "sketch.png")
    activate_scene(SCENE_NAME)
    export_image(output_path)
    puts "✓ sketch.png"
    output_path
  end

  # Экспорт маски surfaces (стены + пол, без объектов)
  def self.export_surfaces_mask
    output_path = File.join(OUTPUT_DIR, "mask_surfaces.png")
    
    saved = save_visibility
    begin
      activate_scene(SCENE_NAME)
      
      # Скрыть все объекты, оставить только surfaces
      OBJECTS.keys.each { |pid| hide_entity(pid) }
      SURFACES.keys.each { |pid| show_entity(pid) }
      
      view.refresh
      export_image(output_path)
      puts "✓ mask_surfaces.png (walls + floor, no objects)"
    ensure
      restore_visibility(saved)
    end
    
    output_path
  end

  # Экспорт маски одного объекта (с окклюзией от объектов "впереди")
  def self.export_object_mask(pid, name, occluders = [])
    output_path = File.join(OUTPUT_DIR, "mask_#{name}.png")
    
    saved = save_visibility
    begin
      activate_scene(SCENE_NAME)
      
      # Скрыть всё
      hide_all_known_entities
      
      # Показать целевой объект
      show_entity(pid)
      
      # Показать объекты-окклюдеры (они перекроют часть целевого)
      occluders.each { |occ_pid| show_entity(occ_pid) }
      
      view.refresh
      export_image(output_path)
      
      occ_names = occluders.map { |p| ALL_ENTITIES[p] }.compact.join(', ')
      puts "✓ mask_#{name}.png" + (occ_names.empty? ? "" : " (occluded by: #{occ_names})")
    ensure
      restore_visibility(saved)
    end
    
    output_path
  end

  # Экспорт маски walls (с окклюзией от всех объектов)
  def self.export_walls_mask
    output_path = File.join(OUTPUT_DIR, "mask_walls.png")
    
    saved = save_visibility
    begin
      activate_scene(SCENE_NAME)
      
      # Показать только стены
      hide_all_known_entities
      show_entity(36696)  # walls
      
      # Показать все объекты как окклюдеры
      OBJECTS.keys.each { |pid| show_entity(pid) }
      
      view.refresh
      export_image(output_path)
      puts "✓ mask_walls.png (with object occlusion)"
    ensure
      restore_visibility(saved)
    end
    
    output_path
  end

  # Экспорт маски floor (с окклюзией от всех объектов)
  def self.export_floor_mask
    output_path = File.join(OUTPUT_DIR, "mask_floor.png")
    
    saved = save_visibility
    begin
      activate_scene(SCENE_NAME)
      
      # Показать только пол
      hide_all_known_entities
      show_entity(36828)  # floor
      
      # Показать все объекты как окклюдеры
      OBJECTS.keys.each { |pid| show_entity(pid) }
      
      view.refresh
      export_image(output_path)
      puts "✓ mask_floor.png (with object occlusion)"
    ensure
      restore_visibility(saved)
    end
    
    output_path
  end

  # ============================================
  # MAIN COMMANDS
  # ============================================

  def self.preview
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   SCENE BUNDLE EXPORTER v3               ║"
    puts "║   LAYERED: Surfaces → Objects            ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    puts "Output:     #{OUTPUT_DIR}"
    puts "Resolution: #{EXPORT_WIDTH}x#{EXPORT_HEIGHT}"
    puts ""
    
    puts "=== SURFACES ==="
    SURFACES.each do |pid, name|
      entity = find_by_pid(pid)
      status = entity ? "✓" : "✗"
      puts "  #{status} #{name} (PID #{pid})"
    end
    
    puts ""
    puts "=== OBJECTS ==="
    OBJECTS.each do |pid, name|
      entity = find_by_pid(pid)
      status = entity ? "✓" : "✗"
      puts "  #{status} #{name} (PID #{pid})"
    end
    
    puts ""
    puts "Commands:"
    puts "  SceneBundleExporter.export_bundle"
    puts "  SceneBundleExporter.export_sketch"
    puts "  SceneBundleExporter.export_surfaces_mask"
  end

  def self.export_bundle
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   EXPORTING LAYERED BUNDLE               ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    FileUtils.mkdir_p(OUTPUT_DIR)
    
    # 1. Full sketch
    puts "=== SKETCH ==="
    export_sketch
    
    # 2. Surfaces mask (walls + floor without objects)
    puts ""
    puts "=== SURFACES ==="
    export_surfaces_mask
    export_walls_mask
    export_floor_mask
    
    # 3. Object masks (each with occlusion from objects in front)
    puts ""
    puts "=== OBJECTS ==="
    
    # Порядок объектов от заднего к переднему
    object_order = [
      [359764, 'window', []],
      [43754, 'bathtub', []],
      [143585, 'shower', []],
      [229917, 'rainshower', []],
      [352872, 'towel_warmer', []],
      [124416, 'vanity', [471300]],  # vanity occluded by mirror
      [471300, 'mirror', []],
      [424271, 'basket', []]
    ]
    
    object_order.each do |pid, name, occluders|
      export_object_mask(pid, name, occluders)
    end
    
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   EXPORT COMPLETE                        ║"
    puts "╚══════════════════════════════════════════╝"
    
    verify
  end

  def self.verify
    puts ""
    puts "=== FILES ==="
    Dir.glob(File.join(OUTPUT_DIR, "*.png")).sort.each do |f|
      puts "  #{File.basename(f)} (#{File.size(f)/1024} KB)"
    end
  end

end

puts ""
puts "Scene Bundle Exporter v3 loaded!"
puts "Commands:"
puts "  SceneBundleExporter.preview"
puts "  SceneBundleExporter.export_bundle"
