# Scene Bundle Exporter v2 for SketchUp
# FIXES: Masks with proper OCCLUSION — objects in front create holes
#
# Usage in SketchUp Ruby Console:
#   load 'C:/Users/paril/Desktop/scene_bundle_exporter_v2.rb'
#   SceneBundleExporter.preview          
#   SceneBundleExporter.export_bundle    
#   SceneBundleExporter.verify           

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
  
  SCENE_NAME = 'Сцена №1'
  
  # ============================================
  # МАППИНГ ОБЪЕКТОВ (порядок = Z-order, от заднего к переднему)
  # ============================================
  
  # Порядок важен! Задние объекты первыми, передние последними
  # Это нужно для правильной окклюзии
  ENTITY_ORDER = [
    'walls',          # самый задний
    'wall_tiles',     # материал на стенах
    'wall_paint',     # материал на стенах
    'window',
    'floor',
    'bathtub',
    'shower',
    'rainshower',
    'towel_warmer',
    'vanity',
    'mirror',
    'basket'          # самый передний
  ]
  
  # Маппинг PID → имя
  ENTITY_MAP = {
    36696 => 'walls',
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
  
  # Обратный маппинг
  NAME_TO_PID = ENTITY_MAP.invert
  
  # Material-based masks (зоны внутри стен)
  MATERIAL_MASKS = {
    'wall_tiles' => 'Материал1',
    'wall_paint' => '[0131_Silver]',
  }
  
  # Цвета
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
      sleep(0.2)
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
      materials: save_material_colors,
      rendering: save_rendering_options
    }
  end

  def self.restore_all_states(saved)
    restore_material_colors(saved[:materials])
    restore_rendering_options(saved[:rendering])
    view.refresh
  end

  def self.save_material_colors
    colors = {}
    model.materials.each do |mat|
      colors[mat.name] = {
        color: mat.color.to_a,
        alpha: mat.alpha
      }
    end
    colors
  end

  def self.restore_material_colors(saved)
    saved.each do |name, data|
      mat = model.materials[name]
      if mat
        mat.color = Sketchup::Color.new(*data[:color])
        mat.alpha = data[:alpha]
      end
    end
  end

  def self.save_rendering_options
    rendering = model.rendering_options
    opts = {}
    ['BackgroundColor', 'DrawHorizon', 'DrawGround', 'DrawUnderground', 
     'EdgeDisplayMode', 'DrawSilhouettes', 'DisplayInstanceAxes'].each do |key|
      opts[key] = rendering[key]
    end
    opts
  end

  def self.restore_rendering_options(saved)
    rendering = model.rendering_options
    saved.each do |key, value|
      rendering[key] = value rescue nil
    end
  end

  # ============================================
  # НОВАЯ ЛОГИКА: ОККЛЮЗИЯ
  # ============================================

  def self.setup_mask_rendering
    rendering = model.rendering_options
    rendering['BackgroundColor'] = MASK_BLACK
    rendering['DrawHorizon'] = false
    rendering['DrawGround'] = false
    rendering['DrawUnderground'] = false
    rendering['EdgeDisplayMode'] = 0
    rendering['DrawSilhouettes'] = false
    rendering['DisplayInstanceAxes'] = false
  end

  # Получить список объектов ПЕРЕД данным (по Z-order)
  def self.get_occluding_entities(target_name)
    idx = ENTITY_ORDER.index(target_name)
    return [] unless idx
    
    # Все объекты после target в списке = они впереди
    occluders = ENTITY_ORDER[(idx + 1)..-1] || []
    occluders
  end

  # Покрасить entity и все его faces в цвет
  def self.paint_entity(entity, color)
    return unless entity
    
    if entity.respond_to?(:material=)
      entity.material = color
    end
    
    if entity.is_a?(Sketchup::Group)
      paint_all_faces(entity.entities, color)
    elsif entity.is_a?(Sketchup::ComponentInstance)
      # Для компонентов создаём уникальную копию чтобы не менять definition
      entity.make_unique if entity.definition.count_used_instances > 1
      paint_all_faces(entity.definition.entities, color)
    end
  end

  def self.paint_all_faces(entities, color)
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        e.material = color
        e.back_material = color
      elsif e.is_a?(Sketchup::Group)
        paint_all_faces(e.entities, color)
      elsif e.is_a?(Sketchup::ComponentInstance)
        paint_all_faces(e.definition.entities, color)
      end
    end
  end

  # Покрасить все faces с определённым материалом
  def self.paint_faces_by_original_material(entities, original_mat_name, new_color)
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        if (e.material && e.material.name == original_mat_name) ||
           (e.back_material && e.back_material.name == original_mat_name)
          e.material = new_color
          e.back_material = new_color
        end
      elsif e.is_a?(Sketchup::Group)
        paint_faces_by_original_material(e.entities, original_mat_name, new_color)
      elsif e.is_a?(Sketchup::ComponentInstance)
        paint_faces_by_original_material(e.definition.entities, original_mat_name, new_color)
      end
    end
  end

  # ============================================
  # ЭКСПОРТ МАСОК С ОККЛЮЗИЕЙ
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
    
    puts "✓ sketch.png (#{EXPORT_WIDTH}x#{EXPORT_HEIGHT})"
    output_path
  end

  # Экспорт маски entity С УЧЁТОМ ОККЛЮЗИИ
  def self.export_entity_mask(name)
    output_path = File.join(OUTPUT_DIR, "mask_#{name}.png")
    
    pid = NAME_TO_PID[name]
    entity = find_by_pid(pid) if pid
    
    unless entity
      puts "⚠️  #{name}: entity not found (PID #{pid})"
      return nil
    end
    
    saved = save_all_states
    
    begin
      activate_scene(SCENE_NAME)
      setup_mask_rendering
      
      # 1. Покрасить ВСЁ в чёрный
      paint_all_entities_black
      
      # 2. Покрасить целевой объект в белый
      paint_entity(entity, MASK_WHITE)
      
      # 3. Покрасить объекты ПЕРЕД ним в чёрный (они перекроют белый)
      occluders = get_occluding_entities(name)
      occluders.each do |occ_name|
        occ_pid = NAME_TO_PID[occ_name]
        occ_entity = find_by_pid(occ_pid) if occ_pid
        paint_entity(occ_entity, MASK_BLACK) if occ_entity
      end
      
      view.refresh
      export_image(output_path)
      puts "✓ mask_#{name}.png (occluders: #{occluders.join(', ')})"
      
    ensure
      restore_all_states(saved)
    end
    
    output_path
  end

  # Экспорт маски по материалу С УЧЁТОМ ОККЛЮЗИИ
  def self.export_material_mask(name)
    output_path = File.join(OUTPUT_DIR, "mask_#{name}.png")
    
    mat_name = MATERIAL_MASKS[name]
    unless mat_name
      puts "⚠️  #{name}: no material mapping"
      return nil
    end
    
    saved = save_all_states
    
    begin
      activate_scene(SCENE_NAME)
      setup_mask_rendering
      
      # ВАЖНО: сначала найти faces ДО перекраски!
      # 1. Найти все faces с нужным материалом
      target_faces = find_faces_with_material(model.entities, mat_name)
      puts "   Found #{target_faces.length} faces with material '#{mat_name}'"
      
      # 2. Покрасить ВСЁ в чёрный
      paint_all_entities_black
      
      # 3. Покрасить найденные faces в белый
      target_faces.each do |face|
        face.material = MASK_WHITE
        face.back_material = MASK_WHITE
      end
      
      # 4. Покрасить объекты перед стенами в чёрный (окклюзия)
      occluders = get_occluding_entities(name)
      occluders.each do |occ_name|
        occ_pid = NAME_TO_PID[occ_name]
        occ_entity = find_by_pid(occ_pid) if occ_pid
        paint_entity(occ_entity, MASK_BLACK) if occ_entity
      end
      
      view.refresh
      export_image(output_path)
      puts "✓ mask_#{name}.png (material: #{mat_name})"
      
    ensure
      restore_all_states(saved)
    end
    
    output_path
  end

  def self.find_faces_with_material(entities, mat_name)
    faces = []
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        if (e.material && e.material.name == mat_name) ||
           (e.back_material && e.back_material.name == mat_name)
          faces << e
        end
      elsif e.is_a?(Sketchup::Group)
        faces.concat(find_faces_with_material(e.entities, mat_name))
      elsif e.is_a?(Sketchup::ComponentInstance)
        faces.concat(find_faces_with_material(e.definition.entities, mat_name))
      end
    end
    faces
  end

  def self.paint_all_entities_black
    paint_all_faces(model.entities, MASK_BLACK)
  end

  # ============================================
  # ГЛАВНЫЕ КОМАНДЫ
  # ============================================

  def self.preview
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   SCENE BUNDLE EXPORTER v2               ║"
    puts "║   WITH OCCLUSION SUPPORT                 ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    puts "Output:     #{OUTPUT_DIR}"
    puts "Resolution: #{EXPORT_WIDTH}x#{EXPORT_HEIGHT}"
    puts "Scene:      #{SCENE_NAME}"
    puts ""
    
    puts "=== Z-ORDER (back to front) ==="
    ENTITY_ORDER.each_with_index do |name, idx|
      pid = NAME_TO_PID[name]
      mat = MATERIAL_MASKS[name]
      
      if pid
        entity = find_by_pid(pid)
        status = entity ? "✓" : "✗"
        puts "  #{idx+1}. #{status} #{name} (PID #{pid})"
      elsif mat
        m = model.materials[mat]
        status = m ? "✓" : "✗"
        puts "  #{idx+1}. #{status} #{name} (material: #{mat})"
      else
        puts "  #{idx+1}. ? #{name} (unknown)"
      end
    end
    
    puts ""
    puts "Commands:"
    puts "  SceneBundleExporter.export_bundle"
    puts "  SceneBundleExporter.export_one('floor')"
    puts "  SceneBundleExporter.verify"
  end

  def self.export_one(name)
    FileUtils.mkdir_p(OUTPUT_DIR)
    
    if MATERIAL_MASKS.key?(name)
      export_material_mask(name)
    elsif NAME_TO_PID.key?(name)
      export_entity_mask(name)
    else
      puts "⚠️  Unknown entity: #{name}"
    end
  end

  def self.export_bundle
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   EXPORTING BUNDLE WITH OCCLUSION        ║"
    puts "║   Resolution: #{EXPORT_WIDTH}x#{EXPORT_HEIGHT}                 ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    FileUtils.mkdir_p(OUTPUT_DIR)
    exported = []
    
    # 1. Скетч
    puts "=== SKETCH ==="
    export_sketch
    exported << "sketch.png"
    
    # 2. Маски в порядке Z-order
    puts ""
    puts "=== MASKS (with occlusion) ==="
    
    ENTITY_ORDER.each do |name|
      if MATERIAL_MASKS.key?(name)
        if export_material_mask(name)
          exported << "mask_#{name}.png"
        end
      elsif NAME_TO_PID.key?(name)
        if export_entity_mask(name)
          exported << "mask_#{name}.png"
        end
      end
    end
    
    # Итог
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   EXPORT COMPLETE                        ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    puts "Exported #{exported.length} files to:"
    puts OUTPUT_DIR
    puts ""
    
    verify
    exported
  end

  def self.verify
    puts "=== VERIFICATION ==="
    
    # Check sketch
    sketch_path = File.join(OUTPUT_DIR, "sketch.png")
    if File.exist?(sketch_path)
      puts "  ✓ sketch.png (#{File.size(sketch_path)/1024} KB)"
    else
      puts "  ✗ sketch.png MISSING"
    end
    
    # Check masks
    ENTITY_ORDER.each do |name|
      mask_path = File.join(OUTPUT_DIR, "mask_#{name}.png")
      if File.exist?(mask_path)
        puts "  ✓ mask_#{name}.png (#{File.size(mask_path)/1024} KB)"
      else
        puts "  ✗ mask_#{name}.png MISSING"
      end
    end
  end

end

puts ""
puts "╔══════════════════════════════════════════╗"
puts "║   Scene Bundle Exporter v2 loaded!       ║"
puts "║   NOW WITH OCCLUSION SUPPORT             ║"
puts "╚══════════════════════════════════════════╝"
puts ""
puts "Commands:"
puts "  SceneBundleExporter.preview"
puts "  SceneBundleExporter.export_bundle"
puts "  SceneBundleExporter.export_one('floor')"
