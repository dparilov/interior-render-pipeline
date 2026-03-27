# Scene Extractor for SketchUp
# Extracts scene graph, entities, materials, and metadata for AI analysis
#
# Usage in SketchUp Ruby Console:
#   load '/path/to/scene_extractor.rb'
#   SceneExtractor.extract_to_file('/path/to/output/scene_graph.json')
#
# Or extract to clipboard:
#   SceneExtractor.extract_to_clipboard

require 'json'

module SceneExtractor
  VERSION = '1.0.0'
  
  # Main extraction method
  def self.extract(model = nil)
    model ||= Sketchup.active_model
    return { error: 'No model open' } unless model
    
    {
      meta: extract_meta(model),
      materials: extract_materials(model),
      layers: extract_layers(model),
      scenes: extract_scenes(model),
      entities: extract_entities_recursive(model.entities, nil, 0)
    }
  end
  
  # Extract model metadata
  def self.extract_meta(model)
    {
      title: model.title,
      description: model.description,
      path: model.path,
      modified: model.modified?,
      units: model.options['UnitsOptions']['LengthUnit'],
      geo_reference: model.georeferenced?,
      bounds: bounds_to_hash(model.bounds),
      sketchup_version: Sketchup.version,
      extraction_time: Time.now.iso8601,
      extractor_version: VERSION
    }
  end
  
  # Extract all materials
  def self.extract_materials(model)
    model.materials.map do |mat|
      {
        name: mat.name,
        display_name: mat.display_name,
        color: mat.color ? color_to_hash(mat.color) : nil,
        alpha: mat.alpha,
        texture: mat.texture ? texture_to_hash(mat.texture) : nil,
        materialType: mat.materialType
      }
    end
  end
  
  # Extract all layers/tags
  def self.extract_layers(model)
    model.layers.map do |layer|
      {
        name: layer.name,
        visible: layer.visible?,
        color: layer.color ? color_to_hash(layer.color) : nil,
        folder: layer.folder ? layer.folder.name : nil
      }
    end
  end
  
  # Extract all scenes/pages
  def self.extract_scenes(model)
    model.pages.map do |page|
      {
        name: page.name,
        description: page.description,
        use_camera: page.use_camera?,
        camera: page.use_camera? ? camera_to_hash(page.camera) : nil,
        layers_visible: page.layers.select(&:visible?).map(&:name),
        style: page.style ? page.style.name : nil
      }
    end
  end
  
  # Recursively extract entities
  def self.extract_entities_recursive(entities, parent_pid, depth)
    return [] if depth > 20 # Safety limit
    
    result = []
    
    entities.each do |entity|
      case entity
      when Sketchup::Group
        result << extract_group(entity, parent_pid, depth)
      when Sketchup::ComponentInstance
        result << extract_component_instance(entity, parent_pid, depth)
      when Sketchup::Face
        result << extract_face(entity, parent_pid) if depth < 3 # Only top-level faces
      end
    end
    
    result
  end
  
  # Extract group data
  def self.extract_group(group, parent_pid, depth)
    {
      type: 'group',
      persistent_id: safe_persistent_id(group),
      parent_pid: parent_pid,
      name: group.name.to_s.empty? ? nil : group.name,
      layer: group.layer ? group.layer.name : nil,
      visible: group.visible?,
      bounds: bounds_to_hash(group.bounds),
      transformation: transformation_to_hash(group.transformation),
      material: group.material ? group.material.name : nil,
      attributes: extract_attributes(group),
      entities_count: group.entities.count,
      children: extract_entities_recursive(group.entities, safe_persistent_id(group), depth + 1)
    }
  end
  
  # Extract component instance data
  def self.extract_component_instance(instance, parent_pid, depth)
    definition = instance.definition
    
    {
      type: 'component_instance',
      persistent_id: safe_persistent_id(instance),
      parent_pid: parent_pid,
      name: instance.name.to_s.empty? ? nil : instance.name,
      definition_name: definition.name,
      layer: instance.layer ? instance.layer.name : nil,
      visible: instance.visible?,
      bounds: bounds_to_hash(instance.bounds),
      transformation: transformation_to_hash(instance.transformation),
      material: instance.material ? instance.material.name : nil,
      attributes: extract_attributes(instance),
      definition: {
        name: definition.name,
        description: definition.description,
        instances_count: definition.instances.count,
        entities_count: definition.entities.count,
        bounds: bounds_to_hash(definition.bounds)
      },
      children: extract_entities_recursive(definition.entities, safe_persistent_id(instance), depth + 1)
    }
  end
  
  # Extract face data (simplified)
  def self.extract_face(face, parent_pid)
    {
      type: 'face',
      persistent_id: safe_persistent_id(face),
      parent_pid: parent_pid,
      area: face.area,
      material: face.material ? face.material.name : nil,
      back_material: face.back_material ? face.back_material.name : nil,
      normal: vector_to_array(face.normal),
      plane: face.plane,
      vertices_count: face.vertices.count
    }
  end
  
  # Extract attribute dictionaries
  def self.extract_attributes(entity)
    attrs = {}
    entity.attribute_dictionaries&.each do |dict|
      attrs[dict.name] = {}
      dict.each_pair { |k, v| attrs[dict.name][k] = v }
    end
    attrs.empty? ? nil : attrs
  end
  
  # Helper: safe persistent_id (may not exist in older SketchUp)
  def self.safe_persistent_id(entity)
    entity.respond_to?(:persistent_id) ? entity.persistent_id : entity.entityID
  end
  
  # Helper: bounds to hash
  def self.bounds_to_hash(bounds)
    {
      min: point_to_array(bounds.min),
      max: point_to_array(bounds.max),
      width: bounds.width,
      height: bounds.height,
      depth: bounds.depth,
      center: point_to_array(bounds.center)
    }
  end
  
  # Helper: transformation to hash
  def self.transformation_to_hash(transform)
    {
      origin: point_to_array(transform.origin),
      xaxis: vector_to_array(transform.xaxis),
      yaxis: vector_to_array(transform.yaxis),
      zaxis: vector_to_array(transform.zaxis),
      identity: transform.identity?
    }
  end
  
  # Helper: camera to hash
  def self.camera_to_hash(camera)
    {
      eye: point_to_array(camera.eye),
      target: point_to_array(camera.target),
      up: vector_to_array(camera.up),
      fov: camera.fov,
      aspect_ratio: camera.aspect_ratio,
      perspective: camera.perspective?
    }
  end
  
  # Helper: texture to hash
  def self.texture_to_hash(texture)
    {
      filename: texture.filename,
      width: texture.width,
      height: texture.height,
      image_width: texture.image_width,
      image_height: texture.image_height
    }
  end
  
  # Helper: color to hash
  def self.color_to_hash(color)
    {
      red: color.red,
      green: color.green,
      blue: color.blue,
      alpha: color.alpha
    }
  end
  
  # Helper: point to array
  def self.point_to_array(point)
    [point.x.to_f, point.y.to_f, point.z.to_f]
  end
  
  # Helper: vector to array
  def self.vector_to_array(vector)
    [vector.x.to_f, vector.y.to_f, vector.z.to_f]
  end
  
  # Export to file
  def self.extract_to_file(path)
    data = extract
    File.write(path, JSON.pretty_generate(data))
    puts "Scene graph exported to: #{path}"
    puts "Entities: #{count_entities(data[:entities])}"
    path
  end
  
  # Export to clipboard (for easy paste)
  def self.extract_to_clipboard
    data = extract
    json = JSON.pretty_generate(data)
    # Note: clipboard access may require additional setup in SketchUp
    puts json
    puts "\n--- Copy the above JSON ---"
    json
  end
  
  # Count entities recursively
  def self.count_entities(entities)
    count = entities.size
    entities.each do |e|
      count += count_entities(e[:children]) if e[:children]
    end
    count
  end
  
  # Quick summary without full extraction
  def self.summary
    model = Sketchup.active_model
    return puts "No model open" unless model
    
    puts "=" * 50
    puts "Model: #{model.title}"
    puts "Path: #{model.path}"
    puts "=" * 50
    puts "Materials: #{model.materials.count}"
    puts "Layers/Tags: #{model.layers.count}"
    puts "Scenes/Pages: #{model.pages.count}"
    puts "Root entities: #{model.entities.count}"
    puts "=" * 50
    
    # Top-level groups and components
    groups = model.entities.grep(Sketchup::Group)
    components = model.entities.grep(Sketchup::ComponentInstance)
    
    puts "Top-level groups (#{groups.count}):"
    groups.first(20).each { |g| puts "  - #{g.name.empty? ? '(unnamed)' : g.name}" }
    puts "  ... and #{groups.count - 20} more" if groups.count > 20
    
    puts "Top-level components (#{components.count}):"
    components.first(20).each { |c| puts "  - #{c.definition.name}" }
    puts "  ... and #{components.count - 20} more" if components.count > 20
    
    puts "=" * 50
  end
end

# Auto-run summary when loaded
puts "SceneExtractor v#{SceneExtractor::VERSION} loaded"
puts "Commands:"
puts "  SceneExtractor.summary                    - Quick overview"
puts "  SceneExtractor.extract_to_file('/path')   - Export full scene graph"
puts "  SceneExtractor.extract_to_clipboard       - Print JSON to console"
