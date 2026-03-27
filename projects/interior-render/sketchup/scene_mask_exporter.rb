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
  
  # Faces с определёнными материалами (для стен)
  MATERIAL_MASKS = {
    'wall_tiles' => 'Материал1',      # белая плитка Costa Nova
    'wall_paint' => '[0131_Silver]',  # серая краска
    'bathtub_screen' => 'Материал1'   # экран ванны (тот же материал что плитка)
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
      original_style = view.style
      
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
      view.style = original_style if original_style
      
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
      original_states = save_visibility_states
      original_materials = save_face_materials(faces)
      
      # Скрываем всё
      hide_all_entities
      
      # Показываем и красим нужные faces в белый
      faces.each do |face|
        # Показываем родительский контейнер
        show_face_parents(face)
        face.material = MASK_WHITE
        face.back_material = MASK_WHITE
      end
      
      # Фон чёрный через стиль
      apply_mask_style
      
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
      restore_face_materials(faces, original_materials)
      restore_visibility_states(original_states)
      
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
    
    # Включаем режим Shaded (без текстур)
    view.camera.perspective = true
  end

end

puts "Scene Mask Exporter loaded!"
puts "Run: SceneMaskExporter.preview"
