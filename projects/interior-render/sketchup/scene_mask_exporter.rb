# Scene Mask Exporter for SketchUp
# Exports binary masks for each entity (white = object, black = rest)
# Uses existing scene camera for consistent viewpoint
#
# Usage in SketchUp Ruby Console:
#   load 'C:/Users/paril/Desktop/scene_mask_exporter.rb'
#   SceneMaskExporter.preview          # показать список объектов
#   SceneMaskExporter.export_all       # экспортировать все маски
#   SceneMaskExporter.export_one('floor')  # экспортировать одну маску

require 'sketchup'
require 'json'
require 'fileutils'

module SceneMaskExporter
  # Конфигурация - можно менять
  OUTPUT_DIR = 'C:/Users/paril/Desktop/masks'
  IMAGE_WIDTH = 1920
  IMAGE_HEIGHT = 1080
  SCENE_NAME = 'Сцена №1'  # какую камеру использовать
  
  # Цвета для масок
  MASK_WHITE = Sketchup::Color.new(255, 255, 255)
  MASK_BLACK = Sketchup::Color.new(0, 0, 0)
  
  # Маппинг PID → имя (из нашего анализа)
  ENTITY_MAP = {
    36696 => 'walls',         # НОВЫЙ PID - группа стен
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
  
  # Faces с определёнными материалами (для отдельных зон стен)
  MATERIAL_MASKS = {
    'wall_tiles' => 'Материал1',      # белая плитка Costa Nova
    'wall_paint' => '[0131_Silver]',  # серая краска
  }

  def self.model
    Sketchup.active_model
  end

  def self.view
    model.active_view
  end

  def self.preview
    puts "=== Scene Mask Exporter ==="
    puts "Output: #{OUTPUT_DIR}"
    puts "Resolution: #{IMAGE_WIDTH}x#{IMAGE_HEIGHT}"
    puts "Scene: #{SCENE_NAME}"
    puts ""
    puts "=== Entities to export ==="
    
    ENTITY_MAP.each do |pid, name|
      entity = find_by_pid(pid)
      status = entity ? "✓ found" : "✗ NOT FOUND"
      puts "  #{name} (PID #{pid}): #{status}"
    end
    
    puts ""
    puts "=== Material-based masks ==="
    MATERIAL_MASKS.each do |name, mat_name|
      mat = model.materials[mat_name]
      status = mat ? "✓ found" : "✗ NOT FOUND"
      puts "  #{name} (#{mat_name}): #{status}"
    end
    
    puts ""
    puts "Commands:"
    puts "  SceneMaskExporter.export_all"
    puts "  SceneMaskExporter.export_one('floor')"
  end

  def self.find_by_pid(pid)
    find_entity_recursive(model.entities, pid)
  end

  def self.find_entity_recursive(entities, pid)
    entities.each do |e|
      return e if e.respond_to?(:persistent_id) && e.persistent_id == pid
      
      # Рекурсивно ищем в группах и компонентах
      if e.is_a?(Sketchup::Group)
        found = find_entity_recursive(e.entities, pid)
        return found if found
      elsif e.is_a?(Sketchup::ComponentInstance)
        found = find_entity_recursive(e.definition.entities, pid)
        return found if found
      end
    end
    nil
  end

  def self.export_all
    FileUtils.mkdir_p(OUTPUT_DIR) unless File.exist?(OUTPUT_DIR)
    
    # Активируем нужную сцену/камеру
    activate_scene(SCENE_NAME)
    
    results = []
    
    # Экспорт по entities
    ENTITY_MAP.each do |pid, name|
      puts "Exporting #{name}..."
      success = export_entity_mask(pid, name)
      results << { name: name, success: success }
    end
    
    # Экспорт по материалам (для стен)
    MATERIAL_MASKS.each do |name, mat_name|
      puts "Exporting #{name} (by material)..."
      success = export_material_mask(mat_name, name)
      results << { name: name, success: success }
    end
    
    # Отчёт
    puts ""
    puts "=== Export complete ==="
    results.each do |r|
      status = r[:success] ? "✓" : "✗"
      puts "  #{status} #{r[:name]}"
    end
    puts ""
    puts "Files saved to: #{OUTPUT_DIR}"
  end

  def self.export_one(name)
    FileUtils.mkdir_p(OUTPUT_DIR) unless File.exist?(OUTPUT_DIR)
    activate_scene(SCENE_NAME)
    
    # Ищем в entity map
    pid = ENTITY_MAP.key(name)
    if pid
      export_entity_mask(pid, name)
      return
    end
    
    # Ищем в material masks
    mat_name = MATERIAL_MASKS[name]
    if mat_name
      export_material_mask(mat_name, name)
      return
    end
    
    puts "Unknown entity: #{name}"
    puts "Available: #{ENTITY_MAP.values.join(', ')}, #{MATERIAL_MASKS.keys.join(', ')}"
  end

  def self.activate_scene(scene_name)
    page = model.pages[scene_name]
    if page
      model.pages.selected_page = page
      view.refresh
      puts "Activated scene: #{scene_name}"
    else
      puts "Warning: Scene '#{scene_name}' not found, using current view"
    end
  end

  def self.export_entity_mask(pid, name)
    entity = find_by_pid(pid)
    unless entity
      puts "  Entity PID #{pid} not found"
      return false
    end
    
    model.start_operation('Export Mask', true)
    
    begin
      # Сохраняем оригинальные состояния
      original_states = save_visibility_states
      original_rendering = save_rendering_options
      
      # Скрываем ВСЁ
      hide_all_entities
      
      # Показываем только нужный объект
      show_entity(entity)
      
      # Применяем стиль для маски (белый объект, чёрный фон)
      apply_mask_style
      
      # Экспортируем
      output_path = File.join(OUTPUT_DIR, "mask_#{name}.png")
      
      options = {
        filename: output_path,
        width: IMAGE_WIDTH,
        height: IMAGE_HEIGHT,
        antialias: false,
        transparent: false
      }
      
      view.write_image(options)
      puts "  Saved: #{output_path}"
      
      # Восстанавливаем
      restore_visibility_states(original_states)
      restore_rendering_options(original_rendering)
      
      model.commit_operation
      true
      
    rescue => e
      model.abort_operation
      puts "  Error: #{e.message}"
      false
    end
  end

  def self.export_material_mask(material_name, output_name)
    material = model.materials[material_name]
    unless material
      puts "  Material '#{material_name}' not found"
      return false
    end
    
    model.start_operation('Export Material Mask', true)
    
    begin
      # Находим все faces с этим материалом
      faces = find_faces_with_material(model.entities, material)
      puts "  Found #{faces.length} faces with material '#{material_name}'"
      
      if faces.empty?
        puts "  No faces found"
        model.abort_operation
        return false
      end
      
      # Сохраняем состояния
      original_rendering = save_rendering_options
      original_materials = save_all_materials
      
      # Применяем чёрный фон
      apply_mask_style
      
      # Красим ВСЁ в чёрный, кроме нужных faces
      paint_all_black_except(faces)
      
      # Красим нужные faces в белый
      faces.each do |face|
        face.material = MASK_WHITE
        face.back_material = MASK_WHITE
      end
      
      # Экспортируем
      output_path = File.join(OUTPUT_DIR, "mask_#{output_name}.png")
      
      options = {
        filename: output_path,
        width: IMAGE_WIDTH,
        height: IMAGE_HEIGHT,
        antialias: false,
        transparent: false
      }
      
      view.write_image(options)
      puts "  Saved: #{output_path}"
      
      # Восстанавливаем
      restore_all_materials(original_materials)
      restore_rendering_options(original_rendering)
      
      model.commit_operation
      true
      
    rescue => e
      model.abort_operation
      puts "  Error: #{e.message}"
      false
    end
  end

  def self.find_faces_with_material(entities, material, found = [])
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        if e.material == material || e.back_material == material
          found << e
        end
      elsif e.is_a?(Sketchup::Group)
        find_faces_with_material(e.entities, material, found)
      elsif e.is_a?(Sketchup::ComponentInstance)
        find_faces_with_material(e.definition.entities, material, found)
      end
    end
    found
  end

  def self.save_visibility_states
    states = {}
    collect_visibility_recursive(model.entities, states)
    states
  end

  def self.collect_visibility_recursive(entities, states)
    entities.each do |e|
      if e.respond_to?(:visible?)
        states[e] = {
          visible: e.visible?,
          layer_visible: e.layer.visible?
        }
      end
      if e.is_a?(Sketchup::Group)
        collect_visibility_recursive(e.entities, states)
      elsif e.is_a?(Sketchup::ComponentInstance)
        collect_visibility_recursive(e.definition.entities, states)
      end
    end
  end

  def self.restore_visibility_states(states)
    states.each do |entity, state|
      begin
        entity.visible = state[:visible] if entity.respond_to?(:visible=)
        entity.layer.visible = state[:layer_visible] if entity.layer
      rescue
        # Entity may have been deleted
      end
    end
  end

  def self.hide_all_entities
    model.entities.each do |e|
      e.visible = false if e.respond_to?(:visible=)
    end
  end

  def self.show_entity(entity)
    entity.visible = true
    entity.layer.visible = true if entity.layer
    
    # Если это вложенный объект, показываем родителей
    # (для групп/компонентов внутри других)
  end

  def self.show_face_parents(face)
    # Поднимаемся по иерархии и показываем все родительские контейнеры
    parent = face.parent
    while parent && parent != model
      if parent.respond_to?(:visible=)
        parent.visible = true
      end
      if parent.is_a?(Sketchup::ComponentDefinition)
        parent.instances.each { |i| i.visible = true; i.layer.visible = true if i.layer }
      end
      parent = parent.respond_to?(:parent) ? parent.parent : nil
    end
  end

  def self.save_face_materials(faces)
    faces.map { |f| { face: f, front: f.material, back: f.back_material } }
  end

  def self.restore_face_materials(faces, saved)
    saved.each do |s|
      begin
        s[:face].material = s[:front]
        s[:face].back_material = s[:back]
      rescue
        # Face may have been deleted
      end
    end
  end

  def self.save_all_materials
    saved = []
    collect_all_faces(model.entities).each do |face|
      saved << { face: face, front: face.material, back: face.back_material }
    end
    saved
  end

  def self.restore_all_materials(saved)
    saved.each do |s|
      begin
        s[:face].material = s[:front]
        s[:face].back_material = s[:back]
      rescue
        # Face may have been deleted
      end
    end
  end

  def self.collect_all_faces(entities, faces = [])
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        faces << e
      elsif e.is_a?(Sketchup::Group)
        collect_all_faces(e.entities, faces)
      elsif e.is_a?(Sketchup::ComponentInstance)
        collect_all_faces(e.definition.entities, faces)
      end
    end
    faces
  end

  def self.paint_all_black_except(keep_faces)
    collect_all_faces(model.entities).each do |face|
      unless keep_faces.include?(face)
        face.material = MASK_BLACK
        face.back_material = MASK_BLACK
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

  def self.apply_mask_style
    # Устанавливаем чёрный фон и отключаем всё лишнее
    rendering = model.rendering_options
    
    rendering['BackgroundColor'] = MASK_BLACK
    rendering['DrawHorizon'] = false
    rendering['DrawGround'] = false
    rendering['DrawUnderground'] = false
    rendering['EdgeDisplayMode'] = 0  # без рёбер
    rendering['DrawSilhouettes'] = false
    rendering['DisplayInstanceAxes'] = false
  end

  # Экспорт базового скетча (цветной вид сцены)
  def self.export_sketch(output_path = nil)
    output_path ||= File.join(OUTPUT_DIR, "sketch.png")
    FileUtils.mkdir_p(OUTPUT_DIR) unless File.exist?(OUTPUT_DIR)
    
    activate_scene(SCENE_NAME)
    
    options = {
      filename: output_path,
      width: IMAGE_WIDTH,
      height: IMAGE_HEIGHT,
      antialias: true,
      transparent: false
    }
    
    view.write_image(options)
    puts "Exported sketch: #{output_path}"
    output_path
  end

  # Полный экспорт bundle: скетч + все маски
  def self.export_bundle
    puts "=== EXPORTING FULL BUNDLE ==="
    puts "Output: #{OUTPUT_DIR}"
    puts ""
    
    # 1. Экспорт базового скетча
    puts "1. Exporting base sketch..."
    export_sketch
    
    # 2. Экспорт всех масок
    puts ""
    puts "2. Exporting all masks..."
    export_all
    
    puts ""
    puts "=== BUNDLE COMPLETE ==="
    puts "Files:"
    Dir.glob(File.join(OUTPUT_DIR, "*.png")).sort.each do |f| 
      size = File.size(f) / 1024
      puts "  #{File.basename(f)} (#{size} KB)"
    end
  end

end

puts "Scene Mask Exporter loaded!"
puts ""
puts "Commands:"
puts "  SceneMaskExporter.preview        # показать список"
puts "  SceneMaskExporter.export_sketch  # только скетч"
puts "  SceneMaskExporter.export_all     # все маски"
puts "  SceneMaskExporter.export_bundle  # скетч + маски"
