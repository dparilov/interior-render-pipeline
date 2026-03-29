# IRP Extract — Phase 0: Scene Graph Extraction
# 
# Экспортирует:
# - scene_graph.json (все Groups/Components с PIDs, bounds, именами)
# - beauty.png (полный рендер текущей сцены)
#
# Usage:
#   load 'C:/path/to/irp_extract.rb'
#   IRP.extract

require 'sketchup'
require 'json'
require 'fileutils'

module IRP
  OUTPUT_DIR = File.join(ENV['USERPROFILE'] || ENV['HOME'], 'Downloads', 'irp_extract')
  RESOLUTION = [1920, 1080]
  
  def self.model
    Sketchup.active_model
  end
  
  def self.view
    model.active_view
  end
  
  # ============================================
  # SCENE GRAPH EXTRACTION
  # ============================================
  
  def self.extract
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   IRP EXTRACT — Phase 0                  ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    
    FileUtils.mkdir_p(OUTPUT_DIR)
    
    # 1. Extract scene graph
    puts "=== SCENE GRAPH ==="
    scene_graph = extract_scene_graph
    
    graph_path = File.join(OUTPUT_DIR, 'scene_graph.json')
    File.write(graph_path, JSON.pretty_generate(scene_graph))
    puts "  ✓ scene_graph.json (#{scene_graph[:entities].length} entities)"
    
    # 2. Export beauty render
    puts ""
    puts "=== BEAUTY RENDER ==="
    beauty_path = File.join(OUTPUT_DIR, 'beauty.png')
    export_image(beauty_path)
    puts "  ✓ beauty.png"
    
    # 3. Export camera info
    puts ""
    puts "=== CAMERA ==="
    camera_info = extract_camera
    puts "  Scene: #{camera_info[:scene_name]}"
    puts "  Position: #{camera_info[:eye].map { |v| v.round(2) }}"
    
    # Summary
    puts ""
    puts "╔══════════════════════════════════════════╗"
    puts "║   EXTRACTION COMPLETE                    ║"
    puts "╚══════════════════════════════════════════╝"
    puts ""
    puts "Output: #{OUTPUT_DIR}"
    puts ""
    puts "Files:"
    Dir.glob(File.join(OUTPUT_DIR, '*')).each do |f|
      size_kb = File.size(f) / 1024
      puts "  #{File.basename(f)} (#{size_kb} KB)"
    end
    puts ""
    puts "Next: Send scene_graph.json + beauty.png for intelligent mapping"
    
    scene_graph
  end
  
  def self.extract_scene_graph
    entities = []
    
    walk_entities(model.entities, nil, entities, 0)
    
    # Current scene info
    current_scene = model.pages.selected_page
    
    {
      model_name: model.name,
      model_path: model.path,
      scene_name: current_scene ? current_scene.name : 'Default',
      resolution: RESOLUTION,
      unit: model.options['UnitsOptions']['LengthUnit'],
      entities: entities,
      camera: extract_camera,
      extracted_at: Time.now.iso8601
    }
  end
  
  def self.walk_entities(entities, parent_pid, out, depth, transform = nil)
    transform ||= Geom::Transformation.new
    
    entities.each do |e|
      # Include Groups, ComponentInstances, and Faces for full picture
      if e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        
        # Get world transform
        world_transform = transform * e.transformation
        
        # Get bounds in world coordinates
        bounds = e.bounds
        
        # Get name
        name = if e.is_a?(Sketchup::Group)
          e.name.to_s.empty? ? nil : e.name
        else
          e.definition.name
        end
        
        # Component definition name (for components)
        definition_name = e.is_a?(Sketchup::ComponentInstance) ? e.definition.name : nil
        
        # Count faces inside
        child_entities = e.is_a?(Sketchup::Group) ? e.entities : e.definition.entities
        face_count = count_faces_recursive(child_entities)
        child_group_count = child_entities.count { |c| c.is_a?(Sketchup::Group) || c.is_a?(Sketchup::ComponentInstance) }
        
        # Get position from transformation
        origin = world_transform.origin
        
        entity_data = {
          pid: e.persistent_id,
          type: e.class.to_s.split('::').last,
          name: name,
          definition_name: definition_name,
          parent_pid: parent_pid,
          depth: depth,
          visible: e.visible?,
          layer: e.layer&.name,
          material: e.material&.display_name,
          face_count: face_count,
          child_count: child_group_count,
          position: {
            x: origin.x.to_m.round(3),
            y: origin.y.to_m.round(3),
            z: origin.z.to_m.round(3)
          },
          bounds: {
            min: [bounds.min.x.to_m, bounds.min.y.to_m, bounds.min.z.to_m].map { |v| v.round(3) },
            max: [bounds.max.x.to_m, bounds.max.y.to_m, bounds.max.z.to_m].map { |v| v.round(3) },
            width: bounds.width.to_m.round(3),
            height: bounds.height.to_m.round(3),
            depth: bounds.depth.to_m.round(3),
            volume: (bounds.width.to_m * bounds.height.to_m * bounds.depth.to_m).round(4)
          }
        }
        
        out << entity_data
        
        # Recurse into children with accumulated transform
        walk_entities(child_entities, e.persistent_id, out, depth + 1, world_transform)
      end
    end
  end
  
  def self.count_faces_recursive(entities)
    count = 0
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        count += 1
      elsif e.is_a?(Sketchup::Group)
        count += count_faces_recursive(e.entities)
      elsif e.is_a?(Sketchup::ComponentInstance)
        count += count_faces_recursive(e.definition.entities)
      end
    end
    count
  end
  
  def self.extract_camera
    camera = view.camera
    page = model.pages.selected_page
    
    {
      scene_name: page ? page.name : 'Default',
      eye: [camera.eye.x.to_m, camera.eye.y.to_m, camera.eye.z.to_m],
      target: [camera.target.x.to_m, camera.target.y.to_m, camera.target.z.to_m],
      up: [camera.up.x, camera.up.y, camera.up.z],
      fov: camera.fov,
      aspect_ratio: camera.aspect_ratio,
      perspective: camera.perspective?
    }
  end
  
  def self.export_image(path)
    options = {
      filename: path,
      width: RESOLUTION[0],
      height: RESOLUTION[1],
      antialias: true,
      transparent: false
    }
    view.write_image(options)
  end
end

# Startup
puts ""
puts "╔══════════════════════════════════════════╗"
puts "║   IRP Extract loaded                     ║"
puts "╚══════════════════════════════════════════╝"
puts ""
puts "Command: IRP.extract"
puts "Output: #{IRP::OUTPUT_DIR}"
puts ""
