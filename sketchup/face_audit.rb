# Face-level audit for pid=36696 (walls)
# Run in SketchUp Ruby Console:
#   load '/path/to/face_audit.rb'
#   FaceAudit.run

require 'json'

module FaceAudit
  TARGET_PID = 36696
  OUTPUT_FILE = File.expand_path("~/sketchup-share/face_audit_36696.json")
  
  def self.run
    model = Sketchup.active_model
    
    puts "=" * 60
    puts "FACE-LEVEL AUDIT FOR PID=#{TARGET_PID}"
    puts "=" * 60
    
    # Find the target entity
    entity = model.find_entity_by_persistent_id(TARGET_PID)
    
    if entity.nil?
      puts "ERROR: Entity with pid=#{TARGET_PID} not found!"
      return nil
    end
    
    puts "Found: #{entity.class} (#{entity.name.empty? ? 'unnamed' : entity.name})"
    
    # Get inner entities
    inner = case entity
      when Sketchup::Group then entity.entities
      when Sketchup::ComponentInstance then entity.definition.entities
      else
        puts "ERROR: Entity is not a Group or ComponentInstance"
        return nil
    end
    
    # Collect all faces
    faces = inner.grep(Sketchup::Face)
    puts "Total faces inside group: #{faces.length}"
    
    # Group material assigned at entity level
    group_material = entity.material
    puts "Group-level material: #{group_material ? group_material.display_name : 'none'}"
    
    # Analyze each face
    face_data = []
    material_stats = Hash.new { |h, k| h[k] = { count: 0, area: 0.0, faces: [] } }
    
    faces.each_with_index do |face, idx|
      # Get materials
      front_mat = face.material
      back_mat = face.back_material
      
      # Effective material (front, then back, then group)
      effective_mat = front_mat || back_mat || group_material
      mat_name = effective_mat ? effective_mat.display_name : 'none'
      
      # Get geometry info
      area = face.area  # in square inches
      area_m2 = area * 0.00064516  # convert to m²
      
      normal = face.normal
      bounds = face.bounds
      center = bounds.center
      
      # Classify by normal (vertical vs horizontal)
      is_vertical = normal.z.abs < 0.1
      is_horizontal = normal.z.abs > 0.9
      
      face_info = {
        index: idx,
        front_material: front_mat ? front_mat.display_name : nil,
        back_material: back_mat ? back_mat.display_name : nil,
        effective_material: mat_name,
        area_m2: area_m2.round(4),
        normal: [normal.x.round(3), normal.y.round(3), normal.z.round(3)],
        center: [center.x.to_m.round(3), center.y.to_m.round(3), center.z.to_m.round(3)],
        bounds_min: [bounds.min.x.to_m.round(3), bounds.min.y.to_m.round(3), bounds.min.z.to_m.round(3)],
        bounds_max: [bounds.max.x.to_m.round(3), bounds.max.y.to_m.round(3), bounds.max.z.to_m.round(3)],
        is_vertical: is_vertical,
        is_horizontal: is_horizontal,
        vertices: face.vertices.length
      }
      
      face_data << face_info
      
      # Aggregate by material
      material_stats[mat_name][:count] += 1
      material_stats[mat_name][:area] += area_m2
      material_stats[mat_name][:faces] << idx
    end
    
    # Print summary
    puts "\n=== MATERIAL SUMMARY ==="
    material_stats.each do |mat, stats|
      puts "  #{mat}: #{stats[:count]} faces, #{stats[:area].round(3)} m²"
    end
    
    # Check for potential tile/upper split
    puts "\n=== SPLIT ANALYSIS ==="
    
    # Group by Z position to see if there's a height-based material split
    z_material_map = Hash.new { |h, k| h[k] = [] }
    face_data.each do |fd|
      z_bucket = (fd[:center][2] * 10).round / 10.0  # bucket by 10cm
      z_material_map[z_bucket] << fd[:effective_material]
    end
    
    puts "Materials by Z height:"
    z_material_map.keys.sort.each do |z|
      mats = z_material_map[z].tally
      puts "  Z=#{z}m: #{mats}"
    end
    
    # Build output
    result = {
      audit_date: Time.now.iso8601,
      target_pid: TARGET_PID,
      entity_type: entity.class.to_s,
      entity_name: entity.name.empty? ? nil : entity.name,
      group_material: group_material ? group_material.display_name : nil,
      total_faces: faces.length,
      material_summary: material_stats.transform_values { |v| { count: v[:count], area_m2: v[:area].round(4) } },
      z_material_distribution: z_material_map.transform_values { |v| v.tally },
      faces: face_data
    }
    
    # Write to file
    File.open(OUTPUT_FILE, 'w') do |f|
      f.write(JSON.pretty_generate(result))
    end
    
    puts "\n✓ Audit saved to: #{OUTPUT_FILE}"
    puts "=" * 60
    
    result
  end
end

puts "FaceAudit module loaded. Run: FaceAudit.run"
