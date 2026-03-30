# IRP Face Materials Extension
# Extends scene_graph.json with per-face material data
#
# Run after IRP.extract to add face_materials to existing scene_graph:
#   load '/path/to/irp_face_materials.rb'
#   IRPFaceMaterials.enhance_scene_graph
#
# Or run standalone:
#   IRPFaceMaterials.export_face_materials

require 'sketchup'
require 'json'

module IRPFaceMaterials
  VERSION = '1.0'
  
  def self.model
    Sketchup.active_model
  end
  
  def self.skp_dir
    File.dirname(model.path)
  end
  
  # Collect face materials for a single entity
  def self.collect_face_materials(entity)
    inner = case entity
      when Sketchup::Group then entity.entities
      when Sketchup::ComponentInstance then entity.definition.entities
      else return nil
    end
    
    materials = {}
    inner.grep(Sketchup::Face).each do |face|
      # Get effective material (front, back, or group)
      mat = face.material || face.back_material || entity.material
      mat_name = mat ? mat.display_name : 'none'
      
      materials[mat_name] ||= {
        count: 0,
        area_m2: 0.0,
        z_values: [],
        faces: []
      }
      
      area_m2 = face.area * 0.00064516
      center = face.bounds.center
      
      materials[mat_name][:count] += 1
      materials[mat_name][:area_m2] += area_m2
      materials[mat_name][:z_values] << center.z.to_m
      materials[mat_name][:faces] << {
        center: [center.x.to_m.round(3), center.y.to_m.round(3), center.z.to_m.round(3)],
        area_m2: area_m2.round(4),
        normal: [face.normal.x.round(3), face.normal.y.round(3), face.normal.z.round(3)],
        is_vertical: face.normal.z.abs < 0.1
      }
    end
    
    # Calculate z ranges and finalize
    materials.transform_values! do |data|
      z = data[:z_values]
      data[:z_min] = z.min.round(3)
      data[:z_max] = z.max.round(3)
      data[:z_avg] = (z.sum / z.length).round(3)
      data[:area_m2] = data[:area_m2].round(4)
      data.delete(:z_values)
      data
    end
    
    materials
  end
  
  # Export face materials for all entities
  def self.export_face_materials(output_path = nil)
    output_path ||= File.join(skp_dir, 'face_materials.json')
    
    puts "=" * 60
    puts "IRP FACE MATERIALS EXPORT v#{VERSION}"
    puts "=" * 60
    
    entities_data = {}
    
    model.entities.each do |e|
      next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
      next if e.hidden?
      
      pid = e.persistent_id
      mats = collect_face_materials(e)
      
      if mats && mats.length > 1  # Only include if multiple materials
        entities_data[pid] = {
          name: e.name.empty? ? nil : e.name,
          type: e.class.to_s.split('::').last,
          face_materials: mats
        }
        
        puts "Entity #{pid}: #{mats.length} materials"
        mats.each do |mat_name, data|
          puts "  #{mat_name}: #{data[:count]} faces, #{data[:area_m2]} m², Z=#{data[:z_min]}-#{data[:z_max]}"
        end
      end
    end
    
    output = {
      version: VERSION,
      export_date: Time.now.iso8601,
      model_name: File.basename(model.path, '.skp'),
      entities_with_multiple_materials: entities_data
    }
    
    File.open(output_path, 'w') { |f| f.write(JSON.pretty_generate(output)) }
    puts "\n✓ Exported to: #{output_path}"
    
    output
  end
  
  # Enhance existing scene_graph.json with face_materials
  def self.enhance_scene_graph(scene_graph_path = nil)
    scene_graph_path ||= File.join(skp_dir, 'irp_extract', 'scene_graph.json')
    
    unless File.exist?(scene_graph_path)
      puts "ERROR: scene_graph.json not found at #{scene_graph_path}"
      return nil
    end
    
    puts "=" * 60
    puts "ENHANCING SCENE_GRAPH WITH FACE MATERIALS"
    puts "=" * 60
    
    sg = JSON.parse(File.read(scene_graph_path))
    enhanced_count = 0
    
    sg['entities'].each do |entity_data|
      pid = entity_data['pid']
      entity = model.find_entity_by_persistent_id(pid)
      next unless entity
      
      mats = collect_face_materials(entity)
      if mats && mats.length > 1
        entity_data['face_materials'] = mats
        enhanced_count += 1
        puts "Enhanced pid=#{pid}: #{mats.length} materials"
      end
    end
    
    # Add version marker
    sg['face_materials_version'] = VERSION
    sg['face_materials_date'] = Time.now.iso8601
    
    # Save enhanced version
    enhanced_path = scene_graph_path.sub('.json', '_enhanced.json')
    File.open(enhanced_path, 'w') { |f| f.write(JSON.pretty_generate(sg)) }
    
    puts "\n✓ Enhanced #{enhanced_count} entities"
    puts "✓ Saved to: #{enhanced_path}"
    
    sg
  end
end

puts "IRPFaceMaterials loaded."
puts "Commands:"
puts "  IRPFaceMaterials.export_face_materials   # Export face materials JSON"
puts "  IRPFaceMaterials.enhance_scene_graph     # Add face_materials to scene_graph.json"
