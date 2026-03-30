# Face Region Export for IRP
# Generates masks based on per-face material semantics
#
# Run in SketchUp Ruby Console:
#   load '/path/to/face_region_export.rb'
#   FaceRegionExport.run
#
# This extends IRP export to support semantic regions within a single object.

require 'sketchup'
require 'json'
require 'fileutils'

module FaceRegionExport
  VERSION = '1.0'
  RESOLUTION = [1920, 1080]
  
  # Configuration for bathroom_01 wall split
  WALL_REGIONS = {
    'Материал1' => {
      name: 'walls_tile',
      role: 'surface.walls_tile',
      description: 'White Costa Nova subway tiles (lower wall)',
      reference: 'references/wall_tiles.png',
      critical: true
    },
    '0131_Серебристый' => {
      name: 'walls_upper', 
      role: 'surface.walls_upper',
      description: 'Gray painted wall (upper portion)',
      reference: nil,
      critical: true
    }
  }
  
  def self.model
    Sketchup.active_model
  end
  
  def self.view
    model.active_view
  end
  
  def self.skp_dir
    File.dirname(model.path)
  end
  
  def self.run(target_pid = 36696)
    puts "=" * 60
    puts "FACE REGION EXPORT v#{VERSION}"
    puts "Target: pid=#{target_pid}"
    puts "=" * 60
    
    entity = model.find_entity_by_persistent_id(target_pid)
    unless entity
      puts "ERROR: Entity #{target_pid} not found"
      return nil
    end
    
    inner = case entity
      when Sketchup::Group then entity.entities
      when Sketchup::ComponentInstance then entity.definition.entities
    end
    
    faces = inner.grep(Sketchup::Face)
    puts "Found #{faces.length} faces in group"
    
    # Group faces by material
    face_groups = {}
    faces.each do |face|
      mat = face.material || face.back_material || entity.material
      mat_name = mat ? mat.display_name : 'none'
      face_groups[mat_name] ||= []
      face_groups[mat_name] << face
    end
    
    puts "\nMaterials found:"
    face_groups.each do |mat, faces|
      total_area = faces.sum { |f| f.area * 0.00064516 }
      puts "  #{mat}: #{faces.length} faces, #{total_area.round(2)} m²"
    end
    
    # Build region metadata
    regions = []
    WALL_REGIONS.each do |mat_name, config|
      mat_faces = face_groups[mat_name] || []
      next if mat_faces.empty?
      
      z_values = mat_faces.map { |f| f.bounds.center.z.to_m }
      total_area = mat_faces.sum { |f| f.area * 0.00064516 }
      
      region = {
        parent_pid: target_pid,
        material_name: mat_name,
        semantic_name: config[:name],
        role: config[:role],
        description: config[:description],
        reference: config[:reference],
        critical: config[:critical],
        face_count: mat_faces.length,
        area_m2: total_area.round(4),
        z_min: z_values.min.round(3),
        z_max: z_values.max.round(3),
        z_avg: (z_values.sum / z_values.length).round(3)
      }
      regions << region
      
      puts "\nRegion: #{config[:name]}"
      puts "  Material: #{mat_name}"
      puts "  Faces: #{mat_faces.length}"
      puts "  Area: #{total_area.round(2)} m²"
      puts "  Z range: #{z_values.min.round(2)} - #{z_values.max.round(2)} m"
    end
    
    # Save region metadata
    output = {
      version: VERSION,
      export_date: Time.now.iso8601,
      target_pid: target_pid,
      entity_type: entity.class.to_s,
      resolution: RESOLUTION,
      regions: regions
    }
    
    metadata_path = File.join(skp_dir, 'face_regions.json')
    File.open(metadata_path, 'w') { |f| f.write(JSON.pretty_generate(output)) }
    puts "\n✓ Metadata saved to: #{metadata_path}"
    
    output
  end
  
  def self.export_region_masks(target_pid = 36696, output_dir = nil)
    output_dir ||= File.join(skp_dir, 'region_masks')
    FileUtils.mkdir_p(output_dir)
    
    puts "=" * 60
    puts "EXPORTING REGION MASKS"
    puts "Output: #{output_dir}"
    puts "=" * 60
    
    entity = model.find_entity_by_persistent_id(target_pid)
    unless entity
      puts "ERROR: Entity #{target_pid} not found"
      return nil
    end
    
    inner = case entity
      when Sketchup::Group then entity.entities
      when Sketchup::ComponentInstance then entity.definition.entities
    end
    
    faces = inner.grep(Sketchup::Face)
    
    # Group faces by material
    face_groups = {}
    faces.each do |face|
      mat = face.material || face.back_material || entity.material
      mat_name = mat ? mat.display_name : 'none'
      face_groups[mat_name] ||= []
      face_groups[mat_name] << face
    end
    
    # Create white material for masking
    white = Sketchup::Color.new(255, 255, 255)
    
    exported = []
    
    WALL_REGIONS.each do |mat_name, config|
      mat_faces = face_groups[mat_name] || []
      next if mat_faces.empty?
      
      puts "\nExporting: #{config[:name]}"
      
      # Hide everything
      model.entities.each { |e| e.hidden = true if e.respond_to?(:hidden=) }
      
      # Show and paint target faces white
      entity.hidden = false
      
      model.start_operation('Export Region Mask', true)
      
      # Store original materials
      original_materials = {}
      inner.grep(Sketchup::Face).each do |face|
        original_materials[face] = [face.material, face.back_material]
        face.material = nil
        face.back_material = nil
      end
      
      # Paint only the target material faces white
      mat_faces.each do |face|
        face.material = white
        face.back_material = white
      end
      
      # Export
      mask_path = File.join(output_dir, "#{config[:name]}.png")
      view.write_image(mask_path, RESOLUTION[0], RESOLUTION[1], true)
      puts "  ✓ #{mask_path}"
      
      exported << {
        name: config[:name],
        path: mask_path,
        faces: mat_faces.length
      }
      
      # Restore original materials
      original_materials.each do |face, mats|
        face.material = mats[0]
        face.back_material = mats[1]
      end
      
      model.abort_operation
    end
    
    # Restore visibility
    model.entities.each { |e| e.hidden = false if e.respond_to?(:hidden=) }
    
    puts "\n✓ Exported #{exported.length} region masks"
    exported
  end
end

puts "FaceRegionExport loaded."
puts "Commands:"
puts "  FaceRegionExport.run            # Generate region metadata"
puts "  FaceRegionExport.export_region_masks  # Export mask images"
