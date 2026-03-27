# Scene Extractor v2.0 - Deep recursive traversal
# Extracts full scene graph from SketchUp model with unlimited depth

module SceneExtractor
  VERSION = "2.0.0"
  
  # Max depth to prevent infinite recursion (SketchUp models rarely go deeper than 10)
  MAX_DEPTH = 20
  
  def self.summary
    model = Sketchup.active_model
    return "No model open" unless model
    
    puts "=" * 50
    puts "Model: #{model.title}"
    puts "=" * 50
    
    # Count all entities recursively
    stats = {components: 0, groups: 0, faces: 0, edges: 0, max_depth: 0}
    count_recursive(model.entities, stats, 0)
    
    puts "\n=== RECURSIVE STATS ==="
    puts "Components: #{stats[:components]}"
    puts "Groups: #{stats[:groups]}"
    puts "Faces: #{stats[:faces]}"
    puts "Max depth: #{stats[:max_depth]}"
    
    puts "\n=== TOP-LEVEL ENTITIES ==="
    model.entities.each do |e|
      case e
      when Sketchup::ComponentInstance
        puts "  [C] #{e.definition.name}"
      when Sketchup::Group
        name = e.name.empty? ? "(unnamed group)" : e.name
        puts "  [G] #{name}"
      end
    end
    
    puts "\n=== ALL COMPONENTS (nested) ==="
    find_all_components(model.entities, 0).each do |info|
      indent = "  " * info[:depth]
      puts "#{indent}[depth #{info[:depth]}] #{info[:name]} (#{info[:path]})"
    end
    
    puts "=" * 50
  end
  
  def self.count_recursive(entities, stats, depth)
    stats[:max_depth] = [stats[:max_depth], depth].max
    return if depth > MAX_DEPTH
    
    entities.each do |e|
      case e
      when Sketchup::ComponentInstance
        stats[:components] += 1
        count_recursive(e.definition.entities, stats, depth + 1)
      when Sketchup::Group
        stats[:groups] += 1
        count_recursive(e.entities, stats, depth + 1)
      when Sketchup::Face
        stats[:faces] += 1
      when Sketchup::Edge
        stats[:edges] += 1
      end
    end
  end
  
  def self.find_all_components(entities, depth, path = "root")
    results = []
    return results if depth > MAX_DEPTH
    
    entities.each do |e|
      case e
      when Sketchup::ComponentInstance
        name = e.definition.name
        current_path = "#{path}/#{name}"
        results << {name: name, depth: depth, path: current_path, entity: e}
        results += find_all_components(e.definition.entities, depth + 1, current_path)
      when Sketchup::Group
        gname = e.name.empty? ? "group_#{e.persistent_id}" : e.name
        current_path = "#{path}/#{gname}"
        results += find_all_components(e.entities, depth + 1, current_path)
      end
    end
    
    results
  end
  
  def self.extract_to_file(path)
    model = Sketchup.active_model
    return "No model open" unless model
    
    data = extract_full(model)
    
    File.open(path, 'w:UTF-8') do |f|
      f.write(JSON.pretty_generate(data))
    end
    
    puts "Exported to: #{path}"
    puts "Size: #{File.size(path)} bytes"
  end
  
  def self.extract_full(model)
    {
      meta: extract_meta(model),
      materials: extract_materials(model),
      layers: extract_layers(model),
      scenes: extract_scenes(model),
      entities: extract_entities_recursive(model.entities, 0, "root"),
      component_index: build_component_index(model)
    }
  end
  
  def self.extract_meta(model)
    bounds = model.bounds
    {
      title: model.title,
      description: model.description,
      path: model.path,
      modified: model.modified?,
      units: model.options["UnitsOptions"]["LengthUnit"],
      geo_reference: model.georeferenced?,
      bounds: format_bounds(bounds),
      sketchup_version: Sketchup.version,
      extraction_time: Time.now.iso8601,
      extractor_version: VERSION
    }
  end
  
  def self.extract_materials(model)
    model.materials.map do |mat|
      {
        name: mat.name,
        display_name: mat.display_name,
        color: mat.color ? {
          red: mat.color.red,
          green: mat.color.green,
          blue: mat.color.blue,
          alpha: mat.color.alpha
        } : nil,
        alpha: mat.alpha,
        texture: mat.texture ? {
          filename: mat.texture.filename,
          width: mat.texture.width,
          height: mat.texture.height,
          image_width: mat.texture.image_width,
          image_height: mat.texture.image_height
        } : nil,
        materialType: mat.materialType
      }
    end
  end
  
  def self.extract_layers(model)
    model.layers.map do |layer|
      {
        name: layer.name,
        visible: layer.visible?,
        color: layer.color ? {
          red: layer.color.red,
          green: layer.color.green,
          blue: layer.color.blue,
          alpha: layer.color.alpha
        } : nil,
        folder: layer.folder ? layer.folder.name : nil
      }
    end
  end
  
  def self.extract_scenes(model)
    model.pages.map do |page|
      {
        name: page.name,
        description: page.description,
        use_camera: page.use_camera?,
        camera: page.use_camera? ? {
          eye: page.camera.eye.to_a,
          target: page.camera.target.to_a,
          up: page.camera.up.to_a,
          fov: page.camera.fov,
          aspect_ratio: page.camera.aspect_ratio,
          perspective: page.camera.perspective?
        } : nil,
        layers_visible: page.layers.select(&:visible?).map(&:name),
        style: page.style ? page.style.name : nil
      }
    end
  end
  
  def self.extract_entities_recursive(entities, depth, path)
    return [] if depth > MAX_DEPTH
    
    results = []
    
    entities.each do |e|
      case e
      when Sketchup::ComponentInstance
        results << extract_component_deep(e, depth, path)
      when Sketchup::Group
        results << extract_group_deep(e, depth, path)
      when Sketchup::Face
        # Only include faces at top level or depth 1 for walls/floors
        if depth <= 1
          results << extract_face_summary(e)
        end
      end
    end
    
    results
  end
  
  def self.extract_component_deep(comp, depth, path)
    defn = comp.definition
    name = defn.name
    current_path = "#{path}/#{name}"
    
    data = {
      type: "component_instance",
      persistent_id: comp.persistent_id,
      depth: depth,
      path: current_path,
      name: comp.name.empty? ? nil : comp.name,
      definition_name: name,
      layer: comp.layer.name,
      visible: comp.visible?,
      bounds: format_bounds(comp.bounds),
      transformation: extract_transformation(comp.transformation),
      material: comp.material ? comp.material.name : nil,
      attributes: extract_attributes(comp),
      definition: {
        name: defn.name,
        description: defn.description,
        instances_count: defn.instances.count,
        entities_count: defn.entities.count,
        bounds: format_bounds(defn.bounds)
      },
      children: extract_entities_recursive(defn.entities, depth + 1, current_path)
    }
    
    # Add face summary for this component
    data[:face_summary] = summarize_faces(defn.entities)
    
    data
  end
  
  def self.extract_group_deep(group, depth, path)
    name = group.name.empty? ? "group_#{group.persistent_id}" : group.name
    current_path = "#{path}/#{name}"
    
    data = {
      type: "group",
      persistent_id: group.persistent_id,
      depth: depth,
      path: current_path,
      name: group.name.empty? ? nil : group.name,
      layer: group.layer.name,
      visible: group.visible?,
      bounds: format_bounds(group.bounds),
      transformation: extract_transformation(group.transformation),
      material: group.material ? group.material.name : nil,
      children: extract_entities_recursive(group.entities, depth + 1, current_path)
    }
    
    # Add face summary
    data[:face_summary] = summarize_faces(group.entities)
    
    data
  end
  
  def self.summarize_faces(entities)
    materials = Hash.new(0)
    face_count = 0
    total_area = 0
    
    entities.each do |e|
      if e.is_a?(Sketchup::Face)
        face_count += 1
        total_area += e.area
        mat = e.material ? e.material.name : "(default)"
        materials[mat] += 1
      end
    end
    
    {
      face_count: face_count,
      total_area_sqm: (total_area * 0.0254 * 0.0254).round(3),  # sq inches to sq meters
      materials: materials
    }
  end
  
  def self.extract_face_summary(face)
    {
      type: "face",
      persistent_id: face.persistent_id,
      area: face.area,
      material: face.material ? face.material.name : nil,
      back_material: face.back_material ? face.back_material.name : nil,
      vertices_count: face.vertices.count
    }
  end
  
  def self.extract_transformation(t)
    {
      origin: t.origin.to_a,
      xaxis: t.xaxis.to_a,
      yaxis: t.yaxis.to_a,
      zaxis: t.zaxis.to_a,
      identity: t.identity?
    }
  end
  
  def self.extract_attributes(entity)
    result = {}
    entity.attribute_dictionaries&.each do |dict|
      result[dict.name] = {}
      dict.each { |k, v| result[dict.name][k] = v }
    end
    result
  end
  
  def self.format_bounds(bounds)
    return nil unless bounds
    {
      min: bounds.min.to_a,
      max: bounds.max.to_a,
      width: "~ #{(bounds.width * 25.4).round(0)} mm",
      height: "~ #{(bounds.height * 25.4).round(0)} mm",
      depth: "~ #{(bounds.depth * 25.4).round(0)} mm",
      center: bounds.center.to_a
    }
  end
  
  # Build flat index of ALL components in model with their paths
  def self.build_component_index(model)
    index = []
    traverse_for_index(model.entities, 0, "root", index)
    index
  end
  
  def self.traverse_for_index(entities, depth, path, index)
    return if depth > MAX_DEPTH
    
    entities.each do |e|
      case e
      when Sketchup::ComponentInstance
        defn = e.definition
        name = defn.name
        current_path = "#{path}/#{name}"
        
        index << {
          name: name,
          depth: depth,
          path: current_path,
          persistent_id: e.persistent_id,
          bounds: format_bounds(e.bounds),
          layer: e.layer.name,
          visible: e.visible?
        }
        
        traverse_for_index(defn.entities, depth + 1, current_path, index)
        
      when Sketchup::Group
        gname = e.name.empty? ? "group_#{e.persistent_id}" : e.name
        current_path = "#{path}/#{gname}"
        traverse_for_index(e.entities, depth + 1, current_path, index)
      end
    end
  end
  
  puts "SceneExtractor v#{VERSION} loaded"
  puts "Commands:"
  puts "  SceneExtractor.summary                    - Deep overview with all nested components"
  puts "  SceneExtractor.extract_to_file('/path')   - Export full scene graph"
end
