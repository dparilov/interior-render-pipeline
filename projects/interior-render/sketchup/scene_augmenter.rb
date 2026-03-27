# Scene Augmenter for SketchUp
# Автоматически именует группы и подготавливает модель для рендера
#
# Usage in SketchUp Ruby Console:
#   load '/path/to/scene_augmenter.rb'
#   SceneAugmenter.run

module SceneAugmenter
  VERSION = '1.0.0'
  
  # Маппинг PID -> имя (из анализа модели "Большой проспект ВО")
  RENAME_MAP = {
    36696 => 'walls',
    36828 => 'floor', 
    124416 => 'vanity',
    352872 => 'towel_warmer',
    359764 => 'window'
  }
  
  # Компоненты для скрытия
  HIDE_COMPONENTS = ['Sumele']
  
  def self.run
    model = Sketchup.active_model
    return puts "No model open" unless model
    
    # Одна операция для undo
    model.start_operation('Scene Augmenter', true)
    
    renamed = 0
    hidden = 0
    
    # Переименование групп
    model.entities.each do |entity|
      if entity.respond_to?(:persistent_id)
        pid = entity.persistent_id
        if RENAME_MAP.key?(pid)
          old_name = entity.name.to_s.empty? ? "(unnamed)" : entity.name
          new_name = RENAME_MAP[pid]
          entity.name = new_name
          puts "Renamed: #{old_name} -> #{new_name} (PID #{pid})"
          renamed += 1
        end
      end
      
      # Скрытие Sumele
      if entity.is_a?(Sketchup::ComponentInstance)
        if HIDE_COMPONENTS.include?(entity.definition.name)
          entity.hidden = true
          puts "Hidden: #{entity.definition.name}"
          hidden += 1
        end
      end
    end
    
    model.commit_operation
    
    puts "\n=== DONE ==="
    puts "Renamed: #{renamed} groups"
    puts "Hidden: #{hidden} components"
    puts "\nYou can Undo (Ctrl+Z) if needed."
  end
  
  # Альтернатива: создать layer для скрытия вместо hidden=true
  def self.move_to_hidden_layer
    model = Sketchup.active_model
    return puts "No model open" unless model
    
    model.start_operation('Move to Hidden Layer', true)
    
    # Создаём или находим layer
    hidden_layer = model.layers['_HIDDEN_FOR_RENDER'] || model.layers.add('_HIDDEN_FOR_RENDER')
    hidden_layer.visible = false
    
    moved = 0
    model.entities.each do |entity|
      if entity.is_a?(Sketchup::ComponentInstance)
        if HIDE_COMPONENTS.include?(entity.definition.name)
          entity.layer = hidden_layer
          puts "Moved to hidden layer: #{entity.definition.name}"
          moved += 1
        end
      end
    end
    
    model.commit_operation
    
    puts "\n=== DONE ==="
    puts "Moved #{moved} components to layer '_HIDDEN_FOR_RENDER'"
  end
  
  # Показать текущее состояние
  def self.status
    model = Sketchup.active_model
    return puts "No model open" unless model
    
    puts "=== CURRENT STATE ==="
    
    RENAME_MAP.each do |pid, expected_name|
      found = false
      model.entities.each do |e|
        if e.respond_to?(:persistent_id) && e.persistent_id == pid
          current_name = e.name.to_s.empty? ? "(unnamed)" : e.name
          status = current_name == expected_name ? "✓" : "✗"
          puts "#{status} PID #{pid}: '#{current_name}' (should be '#{expected_name}')"
          found = true
          break
        end
      end
      puts "? PID #{pid}: NOT FOUND" unless found
    end
    
    puts "\nHidden components:"
    model.entities.each do |e|
      if e.is_a?(Sketchup::ComponentInstance) && HIDE_COMPONENTS.include?(e.definition.name)
        status = e.hidden? ? "hidden" : "visible"
        puts "  #{e.definition.name}: #{status}"
      end
    end
  end
end

puts "SceneAugmenter v#{SceneAugmenter::VERSION} loaded"
puts "Commands:"
puts "  SceneAugmenter.status              - Show current state"
puts "  SceneAugmenter.run                 - Rename groups + hide Sumele"
puts "  SceneAugmenter.move_to_hidden_layer - Alternative: move to hidden layer"
