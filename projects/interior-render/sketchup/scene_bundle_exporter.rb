# Scene Bundle Exporter for SketchUp
# Exports complete rendering bundle: sketch + masks at SAME resolution
#
# Usage in SketchUp Ruby Console:
#   load 'C:/Users/paril/Desktop/scene_bundle_exporter.rb'
#   SceneBundleExporter.preview          # показать список объектов
#   SceneBundleExporter.export_bundle    # экспортировать всё
#   SceneBundleExporter.verify           # верифицировать экспорт

require 'sketchup'
require 'json'
require 'fileutils'

module SceneBundleExporter
  # ============================================
  # КОНФИГУРАЦИЯ — ЕДИНОЕ РАЗРЕШЕНИЕ
  # ============================================
  OUTPUT_DIR = 'C:/Users/paril/Desktop/bundle'
  
  # ВАЖНО: одинаковое разрешение для скетча и масок!
  EXPORT_WIDTH = 1920
  EXPORT_HEIGHT = 1080
  
  SCENE_NAME = 'Сцена №1'  # какую камеру использовать
  
  # ============================================
  # МАППИНГ ОБЪЕКТОВ
  # ============================================
  
  # Маппинг PID → имя (из scene_graph анализа)
  ENTITY_MAP = {
    36696 => 'walls',         # группа стен
    36828 => 'floor',
    124416 => 'vanity', 
    352872 => 'towel_warmer',
    359764 => 'window',
    43754 => 'bathtub',
    471300 => 'mirror',
    143585 => 'shower',
    229917 => 'rainshower',
    424271 => 'basket'
  }
  
  # Faces с определёнными материалами (для зон внутри группы стен)
  MATERIAL_MASKS = {
    'wall_tiles' => 'Материал1',      # белая плитка Costa Nova
    'wall_paint' => '[0131_Silver]',  # серая краска
  }
  
  # Цвета для масок
  MASK_WHITE = Sketchup::Color.new(255, 255, 255)
  MASK_BLACK = Sketchup::Color.new(0, 0, 0)

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
    find_by_pid_recursive(model.entities, pid)
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

  def self.activate_scene(name)
    page = model.pages[name]
    if page
      model.pages.selected_page = page
      view.refresh
      sleep(0.1)  # дать время на обновление
      true
    else
      puts "⚠️  Scene '#{name}' not found!"
      false
    end
  end

  # ============================================
  # СОХРАНЕНИЕ/ВОССТАНОВЛЕНИЕ СОСТОЯНИЯ
  # ============================================
  
  def self.save_all_states
    {
      visibility: save_visibility_states,
      rendering: save_rendering_options,
      materials: save_material_states
    }
  end

  def self.restore_all_states(saved)
    restore_visibility_states(saved[:visibility])
    restore_rendering_options(saved[:rendering])
    restore_material_states(saved[:materials])
  end

  def self.save_visibility_states
    states = {}
    collect_visibility_recursive(model.entities, states)
    # Также сохраняем layers
    model.layers.each do |layer|
      states["layer:#{layer.name}"] = layer.visible?
    end
    states
  end

  def self.collect_visibility_recursive(entities, states)
    entities.each do |e|
      if e.respond_to?(:visible?) && e.respond_to?(:persistent_id)
        states[e.persistent_id] = e.visible?
      end
      if e.is_a?(Sketchup::Group)
        collect_visibility_recursive(e.entities, states)
      elsif e.is_a?(Sketchup::ComponentInstance)
        collect_visibility_recursive(e.definition.entities, states)
      end
    end
  end

  def self.restore_visibility_states(states)
    restore_visibility_recursive(model.entities, states)
    # Восстанавливаем layers
    model.layers.each do |layer|
      key = "layer:#{layer.name}"
      layer.visible = states[key] if states.key?(key)
    end
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

  def self.save_rendering_options
    rendering = model.rendering_options
    {
      'BackgroundColor' => rendering['BackgroundColor'],
      'DrawHorizon' => rendering['DrawHorizon'],
      'DrawGround' => rendering['DrawGround'],
      'DrawUnderground' => rendering['DrawUnderground'],
      'EdgeDisplayMode' => rendering['EdgeDisplayMode'],
      'DrawSilhouettes' => rendering['DrawSilhouettes'],
      'DisplayInstanceAxes' => rendering['DisplayInstanceAxes']
    }
  end

  def self.restore_rendering_options(saved)
    rendering = model.rendering_options
    saved.each do |key, value|
      begin
        rendering[key] = value
      rescue
        # Some options may not be settable
      end
    end
  end

  def self.save_material_states
    states = {}
    model.materials.each do |mat|
      states[mat.name] = mat.color.to_a
    end
    states
  end

  def self.restore_material_states(saved)
    saved.each do |name, color_array|
      mat = model.materials[name]
      mat.color = Sketchup::Color.new(*color_array) if mat
    end
  end

  # ============================================
  # НАСТРОЙКА ДЛЯ МАСОК
  # ============================================

  def self.apply_mask_style
    rendering = model.rendering_options
    rendering['BackgroundColor'] = MASK_BLACK
    rendering['DrawHorizon'] = false
    rendering['DrawGround'] = false
    rendering['DrawUnderground'] = false
    rendering['EdgeDisplayMode'] = 0  # без рёбер
    rendering['DrawSilhouettes'] = false
    rendering['DisplayInstanceAxes'] = false
  end

  def self.hide_all_entities
    hide_recursive(model.entities)
  end

  def self.hide_recursive(entities)
    entities.each do |e|
      e.visible = false if e.respond_to?(:visible=)
    end
  end

  def self.show_entity_for_mask(entity)
    entity.visible = true
    # Устанавливаем белый материал
    if entity.respond_to?(:material=)
      entity.material = MASK_WHITE
    end
    # Для групп — белый на все faces
    if entity.is_a?(Sketchup::Group)
      paint_faces_white(entity.entities)
    elsif entity.is_a?(Sketchup::ComponentInstance)
      paint_faces_white(entity.definition.entities)
    end
    # Показываем родительскую иерархию
    show_parents(entity)
  end

  def self.paint_faces_white(entities)
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        e.material = MASK_WHITE
        e.back_material = MASK_WHITE
      elsif e.is_a?(Sketchup::Group)
        paint_faces_white(e.entities)
      elsif e.is_a?(Sketchup::ComponentInstance)
        paint_faces_white(e.definition.entities)
      end
    end
  end

  def self.show_parents(entity)
    parent = entity.parent
    while parent && parent != model
      if parent.respond_to?(:visible=)
        parent.visible = true
      end
      parent = parent.respond_to?(:parent) ? parent.parent : nil
    end
  end

  # ============================================
  # ЭКСПОРТ ФУНКЦИИ
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

  def self.export_sketch
    output_path = File.join(OUTPUT_DIR, "sketch.png")
    FileUtils.mkdir_p(OUTPUT_DIR) unless File.exist?(OUTPUT_DIR)
    
    activate_scene(SCENE_NAME)
    export_image(output_path)
    
    puts "✓ Exported: sketch.png (#{EXPORT_WIDTH}x#{EXPORT_HEIGHT})"
    output_path
  end

  def self.export_entity_mask(name, entity)
    output_path = File.join(OUTPUT_DIR, "mask_#{name}.png")
    
    saved = save_all_states
    begin
      activate_scene(SCENE_NAME)
      apply_mask_style
      hide_all_entities
      show_entity_for_mask(entity)
      export_image(output_path)
      puts "✓ Exported: mask_#{name}.png"
    ensure
      restore_all_states(saved)
    end
    
    output_path
  end

  def self.export_material_mask(name, material_name)
    output_path = File.join(OUTPUT_DIR, "mask_#{name}.png")
    
    material = model.materials[material_name]
    unless material
      puts "⚠️  Material '#{material_name}' not found, skipping #{name}"
      return nil
    end
    
    saved = save_all_states
    begin
      activate_scene(SCENE_NAME)
      apply_mask_style
      hide_all_entities
      
      # Показываем только faces с этим материалом
      show_faces_with_material(model.entities, material)
      
      export_image(output_path)
      puts "✓ Exported: mask_#{name}.png (material: #{material_name})"
    ensure
      restore_all_states(saved)
    end
    
    output_path
  end

  def self.show_faces_with_material(entities, material)
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        if e.material == material || e.back_material == material
          e.visible = true
          e.material = MASK_WHITE
          e.back_material = MASK_WHITE
          show_parents(e)
        end
      elsif e.is_a?(Sketchup::Group)
        e.visible = true
        show_faces_with_material(e.entities, material)
      elsif e.is_a?(Sketchup::ComponentInstance)
        e.visible = true
        show_faces_with_material(e.definition.entities, material)
      end
    end
  end

  # ============================================
  # ГЛАВНЫЕ КОМАНДЫ
  # ============================================

  def self.preview
    puts "╔══════════════════════════════════════════╗"
    puts "║       SCENE BUNDLE EXPORTER              ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    puts "Output:     #{OUTPUT_DIR}"
    puts "Resolution: #{EXPORT_WIDTH}x#{EXPORT_HEIGHT}"
    puts "Scene:      #{SCENE_NAME}"
    puts ""
    puts "=== ENTITIES ==="
    found = 0
    missing = 0
    ENTITY_MAP.each do |pid, name|
      entity = find_by_pid(pid)
      if entity
        puts "  ✓ #{name} (PID #{pid})"
        found += 1
      else
        puts "  ✗ #{name} (PID #{pid}) — NOT FOUND"
        missing += 1
      end
    end
    
    puts ""
    puts "=== MATERIAL MASKS ==="
    MATERIAL_MASKS.each do |name, mat_name|
      mat = model.materials[mat_name]
      if mat
        puts "  ✓ #{name} (#{mat_name})"
      else
        puts "  ✗ #{name} (#{mat_name}) — NOT FOUND"
      end
    end
    
    puts ""
    puts "Summary: #{found} found, #{missing} missing"
    puts ""
    puts "Commands:"
    puts "  SceneBundleExporter.export_bundle  — export all"
    puts "  SceneBundleExporter.verify         — check exported files"
  end

  def self.export_bundle
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║       EXPORTING BUNDLE                   ║"
    puts "║       Resolution: #{EXPORT_WIDTH}x#{EXPORT_HEIGHT}              ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    FileUtils.mkdir_p(OUTPUT_DIR)
    exported = []
    
    # 1. Экспорт скетча
    puts "=== SKETCH ==="
    if export_sketch
      exported << "sketch.png"
    end
    
    # 2. Экспорт масок по entities
    puts ""
    puts "=== ENTITY MASKS ==="
    ENTITY_MAP.each do |pid, name|
      entity = find_by_pid(pid)
      if entity
        if export_entity_mask(name, entity)
          exported << "mask_#{name}.png"
        end
      else
        puts "⚠️  Skipping #{name} — entity not found"
      end
    end
    
    # 3. Экспорт масок по материалам
    puts ""
    puts "=== MATERIAL MASKS ==="
    MATERIAL_MASKS.each do |name, mat_name|
      if export_material_mask(name, mat_name)
        exported << "mask_#{name}.png"
      end
    end
    
    # Итог
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║       EXPORT COMPLETE                    ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    puts "Exported #{exported.length} files to #{OUTPUT_DIR}:"
    Dir.glob(File.join(OUTPUT_DIR, "*.png")).sort.each do |f|
      size_kb = File.size(f) / 1024
      puts "  #{File.basename(f)} (#{size_kb} KB)"
    end
    
    exported
  end

  def self.verify
    puts ""
    puts "=== VERIFYING EXPORTED FILES ==="
    puts "Directory: #{OUTPUT_DIR}"
    puts ""
    
    expected = ["sketch.png"]
    ENTITY_MAP.values.each { |name| expected << "mask_#{name}.png" }
    MATERIAL_MASKS.keys.each { |name| expected << "mask_#{name}.png" }
    
    ok = 0
    missing = 0
    
    expected.uniq.each do |filename|
      path = File.join(OUTPUT_DIR, filename)
      if File.exist?(path)
        size_kb = File.size(path) / 1024
        puts "  ✓ #{filename} (#{size_kb} KB)"
        ok += 1
      else
        puts "  ✗ #{filename} — MISSING"
        missing += 1
      end
    end
    
    puts ""
    puts "Result: #{ok} OK, #{missing} missing"
    
    if missing == 0
      puts ""
      puts "✓ All files exported successfully!"
      puts "  Copy #{OUTPUT_DIR} to Linux and run render."
    end
  end

end

puts ""
puts "╔══════════════════════════════════════════╗"
puts "║   Scene Bundle Exporter loaded!          ║"
puts "║   Resolution: #{SceneBundleExporter::EXPORT_WIDTH}x#{SceneBundleExporter::EXPORT_HEIGHT}                 ║"
puts "╚══════════════════════════════════════════╝"
puts ""
puts "Commands:"
puts "  SceneBundleExporter.preview        # check entities"
puts "  SceneBundleExporter.export_bundle  # export all"
puts "  SceneBundleExporter.verify         # verify files"
