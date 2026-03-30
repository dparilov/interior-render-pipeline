# Face Material Mask Export for IRP
# Exports masks by projecting face groups with specific materials to camera view
#
# Run in SketchUp Ruby Console:
#   load '/path/to/face_material_mask_export.rb'
#   FaceMaterialMaskExport.export_all
#
# This generates TRUE projected masks from face geometry,
# NOT split from walls.png by Y coordinate.

require 'sketchup'
require 'json'
require 'fileutils'

module FaceMaterialMaskExport
  VERSION = '1.1'
  RESOLUTION = [1920, 1080]
  
  # Configuration for bathroom_01 wall split
  # Maps SKP material names to semantic region names
  MATERIAL_REGIONS = {
    'Материал1' => {
      name: 'walls_tile',
      role: 'surface.walls_tile',
      description: 'White Costa Nova subway tiles (lower wall)'
    },
    '0131_Серебристый' => {
      name: 'walls_upper', 
      role: 'surface.walls_upper',
      description: 'Gray painted wall (upper portion)'
    }
  }
  
  # Target entity
  TARGET_PID = 36696
  
  def self.model
    Sketchup.active_model
  end
  
  def self.view
    model.active_view
  end
  
  def self.skp_dir
    File.dirname(model.path)
  end
  
  def self.output_dir
    dir = File.join(skp_dir, 'face_material_masks')
    FileUtils.mkdir_p(dir)
    dir
  end
  
  def self.find_entity(pid)
    model.find_entity_by_persistent_id(pid)
  end
  
  def self.get_inner_entities(entity)
    case entity
      when Sketchup::Group then entity.entities
      when Sketchup::ComponentInstance then entity.definition.entities
      else nil
    end
  end
  
  def self.get_faces_by_material(entity)
    inner = get_inner_entities(entity)
    return {} unless inner
    
    groups = {}
    inner.grep(Sketchup::Face).each do |face|
      mat = face.material || face.back_material || entity.material
      mat_name = mat ? mat.display_name : 'none'
      groups[mat_name] ||= []
      groups[mat_name] << face
    end
    groups
  end
  
  def self.export_material_mask(entity, material_name, output_name)
    inner = get_inner_entities(entity)
    return false unless inner
    
    puts "  Exporting: #{output_name} (material: #{material_name})"
    
    # Create white color for masking
    white = Sketchup::Color.new(255, 255, 255)
    black = Sketchup::Color.new(0, 0, 0)
    
    model.start_operation('Export Material Mask', true)
    
    begin
      # Step 1: Hide everything in the model
      model.entities.each do |e|
        e.hidden = true if e.respond_to?(:hidden=)
      end
      
      # Step 2: Show only the target entity
      entity.hidden = false
      
      # Step 3: Store original materials and make all faces black/invisible
      original_materials = {}
      inner.grep(Sketchup::Face).each do |face|
        original_materials[face] = {
          front: face.material,
          back: face.back_material
        }
        # Make face invisible (black on black background)
        face.material = black
        face.back_material = black
      end
      
      # Step 4: Paint ONLY faces with target material white
      target_faces = []
      inner.grep(Sketchup::Face).each do |face|
        orig_mat = original_materials[face][:front] || original_materials[face][:back]
        mat_name = orig_mat ? orig_mat.display_name : 'none'
        
        if mat_name == material_name
          face.material = white
          face.back_material = white
          target_faces << face
        end
      end
      
      puts "    Found #{target_faces.length} faces with material '#{material_name}'"
      
      # Step 5: Set background to black for clean mask
      # Note: SketchUp doesn't have easy background control in Ruby API
      # The mask will need post-processing or we rely on hidden geometry
      
      # Step 6: Export the view
      output_path = File.join(output_dir, "#{output_name}.png")
      
      # Refresh view
      view.refresh
      sleep(0.2)
      
      # Write image
      view.write_image(output_path, RESOLUTION[0], RESOLUTION[1], true)
      puts "    ✓ Saved: #{output_path}"
      
      # Step 7: Restore original materials
      original_materials.each do |face, mats|
        face.material = mats[:front]
        face.back_material = mats[:back]
      end
      
      # Step 8: Restore visibility
      model.entities.each do |e|
        e.hidden = false if e.respond_to?(:hidden=)
      end
      
    ensure
      model.abort_operation
    end
    
    true
  end
  
  def self.export_all
    puts "=" * 60
    puts "FACE MATERIAL MASK EXPORT v#{VERSION}"
    puts "Target: pid=#{TARGET_PID}"
    puts "Output: #{output_dir}"
    puts "=" * 60
    
    entity = find_entity(TARGET_PID)
    unless entity
      puts "ERROR: Entity #{TARGET_PID} not found"
      return nil
    end
    
    puts "Found entity: #{entity.class}"
    
    # Get faces grouped by material
    face_groups = get_faces_by_material(entity)
    
    puts "\nMaterials in entity:"
    face_groups.each do |mat, faces|
      region = MATERIAL_REGIONS[mat]
      region_name = region ? " → #{region[:name]}" : ""
      puts "  #{mat}: #{faces.length} faces#{region_name}"
    end
    
    # Export masks for configured regions
    puts "\n" + "-" * 40
    puts "EXPORTING REGION MASKS"
    puts "-" * 40
    
    exported = []
    MATERIAL_REGIONS.each do |mat_name, config|
      if face_groups[mat_name]
        success = export_material_mask(entity, mat_name, config[:name])
        if success
          exported << {
            material: mat_name,
            name: config[:name],
            faces: face_groups[mat_name].length,
            path: File.join(output_dir, "#{config[:name]}.png")
          }
        end
      else
        puts "  SKIP: #{config[:name]} (material '#{mat_name}' not found)"
      end
    end
    
    # Generate metadata
    metadata = {
      version: VERSION,
      export_date: Time.now.iso8601,
      target_pid: TARGET_PID,
      resolution: RESOLUTION,
      method: 'face_projection',
      note: 'Masks generated by projecting face groups to camera view, not by splitting walls.png',
      exports: exported
    }
    
    metadata_path = File.join(output_dir, 'export_metadata.json')
    File.open(metadata_path, 'w') { |f| f.write(JSON.pretty_generate(metadata)) }
    
    puts "\n" + "=" * 60
    puts "EXPORT COMPLETE"
    puts "  Masks: #{exported.length}"
    puts "  Output: #{output_dir}"
    puts "  Metadata: #{metadata_path}"
    puts "=" * 60
    
    exported
  end
end

puts "FaceMaterialMaskExport loaded."
puts "Run: FaceMaterialMaskExport.export_all"
