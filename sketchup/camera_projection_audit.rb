# Camera Projection Audit for IRP
# Projects face vertices to camera image plane and checks for 2D polygon overlap
#
# Run in SketchUp Ruby Console:
#   load '/path/to/camera_projection_audit.rb'
#   CameraProjectionAudit.run
#
# Output: camera_projection_audit.json in SKP directory

require 'sketchup'
require 'json'

module CameraProjectionAudit
  VERSION = '1.0'
  TARGET_PID = 36696
  
  MATERIAL_GROUPS = {
    'Материал1' => 'walls_tile',
    '0131_Серебристый' => 'walls_upper'
  }
  
  def self.model
    Sketchup.active_model
  end
  
  def self.view
    model.active_view
  end
  
  def self.camera
    view.camera
  end
  
  def self.skp_dir
    File.dirname(model.path)
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
  
  # Project a 3D point to 2D screen coordinates
  def self.project_point(point3d)
    # view.screen_coords returns Point3d with x,y as screen coords
    screen_pt = view.screen_coords(point3d)
    [screen_pt.x, screen_pt.y]
  end
  
  # Get face vertices projected to screen
  def self.get_projected_polygon(face, transformation = nil)
    vertices = face.vertices.map { |v| v.position }
    
    # Apply transformation if provided (for nested geometry)
    if transformation
      vertices = vertices.map { |v| transformation * v }
    end
    
    # Project each vertex to screen
    projected = vertices.map { |v| project_point(v) }
    
    # Return as array of [x, y] pairs
    projected
  end
  
  # Calculate 2D polygon area using shoelace formula
  def self.polygon_area(vertices)
    n = vertices.length
    return 0 if n < 3
    
    area = 0.0
    (0...n).each do |i|
      j = (i + 1) % n
      area += vertices[i][0] * vertices[j][1]
      area -= vertices[j][0] * vertices[i][1]
    end
    
    (area.abs / 2.0)
  end
  
  # Get bounding box of polygon
  def self.polygon_bounds(vertices)
    xs = vertices.map { |v| v[0] }
    ys = vertices.map { |v| v[1] }
    {
      min_x: xs.min,
      max_x: xs.max,
      min_y: ys.min,
      max_y: ys.max
    }
  end
  
  # Check if two bounding boxes overlap
  def self.bounds_overlap?(b1, b2)
    !(b1[:max_x] < b2[:min_x] || b2[:max_x] < b1[:min_x] ||
      b1[:max_y] < b2[:min_y] || b2[:max_y] < b1[:min_y])
  end
  
  # Check if point is inside polygon (ray casting)
  def self.point_in_polygon?(point, polygon)
    x, y = point
    n = polygon.length
    inside = false
    
    j = n - 1
    (0...n).each do |i|
      xi, yi = polygon[i]
      xj, yj = polygon[j]
      
      if ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        inside = !inside
      end
      j = i
    end
    
    inside
  end
  
  # Approximate polygon overlap by sampling
  def self.estimate_overlap(poly1, poly2, samples_per_side = 20)
    # Get combined bounds
    b1 = polygon_bounds(poly1)
    b2 = polygon_bounds(poly2)
    
    # Quick check: if bounds don't overlap, polygons don't overlap
    return { overlap_area: 0, overlap_ratio: 0, samples_checked: 0 } unless bounds_overlap?(b1, b2)
    
    # Sample grid in intersection of bounds
    min_x = [b1[:min_x], b2[:min_x]].max
    max_x = [b1[:max_x], b2[:max_x]].min
    min_y = [b1[:min_y], b2[:min_y]].max
    max_y = [b1[:max_y], b2[:max_y]].min
    
    return { overlap_area: 0, overlap_ratio: 0, samples_checked: 0 } if min_x >= max_x || min_y >= max_y
    
    step_x = (max_x - min_x) / samples_per_side.to_f
    step_y = (max_y - min_y) / samples_per_side.to_f
    
    overlap_count = 0
    total_samples = 0
    
    (0..samples_per_side).each do |i|
      (0..samples_per_side).each do |j|
        x = min_x + i * step_x
        y = min_y + j * step_y
        point = [x, y]
        
        in_poly1 = point_in_polygon?(point, poly1)
        in_poly2 = point_in_polygon?(point, poly2)
        
        overlap_count += 1 if in_poly1 && in_poly2
        total_samples += 1
      end
    end
    
    sample_area = step_x * step_y
    overlap_area = overlap_count * sample_area
    
    area1 = polygon_area(poly1)
    area2 = polygon_area(poly2)
    min_area = [area1, area2].min
    
    overlap_ratio = min_area > 0 ? overlap_area / min_area : 0
    
    {
      overlap_area: overlap_area.round(2),
      overlap_ratio: overlap_ratio.round(4),
      samples_checked: total_samples,
      samples_overlapping: overlap_count,
      poly1_area: area1.round(2),
      poly2_area: area2.round(2)
    }
  end
  
  def self.run
    puts "=" * 70
    puts "CAMERA PROJECTION OVERLAP AUDIT v#{VERSION}"
    puts "=" * 70
    
    # Get camera info
    puts "\n--- CAMERA INFO ---"
    puts "Eye: (#{camera.eye.x.to_m.round(3)}, #{camera.eye.y.to_m.round(3)}, #{camera.eye.z.to_m.round(3)})"
    puts "Target: (#{camera.target.x.to_m.round(3)}, #{camera.target.y.to_m.round(3)}, #{camera.target.z.to_m.round(3)})"
    puts "FOV: #{camera.fov.round(2)}"
    puts "View size: #{view.vpwidth} x #{view.vpheight}"
    
    # Find target entity
    entity = find_entity(TARGET_PID)
    unless entity
      puts "ERROR: Entity #{TARGET_PID} not found"
      return nil
    end
    
    inner = get_inner_entities(entity)
    transformation = entity.transformation
    
    # Collect faces by material
    faces_by_material = {}
    inner.grep(Sketchup::Face).each do |face|
      mat = face.material || face.back_material || entity.material
      mat_name = mat ? mat.display_name : 'none'
      faces_by_material[mat_name] ||= []
      faces_by_material[mat_name] << face
    end
    
    puts "\n--- FACES BY MATERIAL ---"
    faces_by_material.each do |mat, faces|
      group_name = MATERIAL_GROUPS[mat] || 'other'
      puts "  #{mat} (#{group_name}): #{faces.length} faces"
    end
    
    # Get projected polygons for each material group
    puts "\n--- PROJECTING FACES ---"
    
    tile_mat = 'Материал1'
    upper_mat = '0131_Серебристый'
    
    tile_faces = faces_by_material[tile_mat] || []
    upper_faces = faces_by_material[upper_mat] || []
    
    tile_polygons = []
    tile_faces.each_with_index do |face, i|
      poly = get_projected_polygon(face, transformation)
      area = polygon_area(poly)
      bounds = polygon_bounds(poly)
      tile_polygons << {
        index: i,
        vertices: poly,
        area: area.round(2),
        bounds: bounds
      }
      puts "  Tile face #{i}: area=#{area.round(0)} px², bounds=(#{bounds[:min_x].round(0)}-#{bounds[:max_x].round(0)}, #{bounds[:min_y].round(0)}-#{bounds[:max_y].round(0)})"
    end
    
    upper_polygons = []
    upper_faces.each_with_index do |face, i|
      poly = get_projected_polygon(face, transformation)
      area = polygon_area(poly)
      bounds = polygon_bounds(poly)
      upper_polygons << {
        index: i,
        vertices: poly,
        area: area.round(2),
        bounds: bounds
      }
      puts "  Upper face #{i}: area=#{area.round(0)} px², bounds=(#{bounds[:min_x].round(0)}-#{bounds[:max_x].round(0)}, #{bounds[:min_y].round(0)}-#{bounds[:max_y].round(0)})"
    end
    
    # Check pairwise overlap
    puts "\n--- CHECKING PAIRWISE OVERLAP ---"
    
    overlapping_pairs = []
    boundary_only_pairs = []
    no_overlap_pairs = []
    
    tile_polygons.each do |tp|
      upper_polygons.each do |up|
        # Quick bounds check
        if bounds_overlap?(tp[:bounds], up[:bounds])
          # Detailed overlap check
          result = estimate_overlap(tp[:vertices], up[:vertices], 30)
          
          if result[:samples_overlapping] > 0
            pair_info = {
              tile_face: tp[:index],
              upper_face: up[:index],
              overlap_samples: result[:samples_overlapping],
              total_samples: result[:samples_checked],
              overlap_area_px2: result[:overlap_area],
              tile_area_px2: tp[:area],
              upper_area_px2: up[:area]
            }
            
            # Classify: true overlap vs boundary contact
            ratio = result[:overlap_ratio] || 0
            if ratio > 0.01  # > 1% overlap
              overlapping_pairs << pair_info
              puts "  OVERLAP: tile[#{tp[:index]}] ↔ upper[#{up[:index]}]: #{result[:samples_overlapping]}/#{result[:samples_checked]} samples, ratio=#{result[:overlap_ratio]}"
            else
              boundary_only_pairs << pair_info
              puts "  BOUNDARY: tile[#{tp[:index]}] ↔ upper[#{up[:index]}]: #{result[:samples_overlapping]} samples (boundary contact)"
            end
          else
            no_overlap_pairs << { tile_face: tp[:index], upper_face: up[:index] }
          end
        end
      end
    end
    
    # Summary
    puts "\n" + "=" * 70
    puts "OVERLAP SUMMARY"
    puts "=" * 70
    puts "True overlapping pairs: #{overlapping_pairs.length}"
    puts "Boundary contact pairs: #{boundary_only_pairs.length}"
    puts "Non-overlapping pairs: #{no_overlap_pairs.length}"
    
    # Calculate total overlap
    total_overlap_area = overlapping_pairs.sum { |p| p[:overlap_area_px2] }
    total_tile_area = tile_polygons.sum { |p| p[:area] }
    total_upper_area = upper_polygons.sum { |p| p[:area] }
    
    puts "\nTotal projected areas:"
    puts "  Tile: #{total_tile_area.round(0)} px²"
    puts "  Upper: #{total_upper_area.round(0)} px²"
    puts "  Overlap: #{total_overlap_area.round(0)} px²"
    
    if [total_tile_area, total_upper_area].min > 0
      overlap_pct = 100 * total_overlap_area / [total_tile_area, total_upper_area].min
      puts "  Overlap %: #{overlap_pct.round(2)}%"
    end
    
    # Generate result
    result = {
      version: VERSION,
      audit_date: Time.now.iso8601,
      camera: {
        eye: [camera.eye.x.to_m, camera.eye.y.to_m, camera.eye.z.to_m].map { |v| v.round(4) },
        target: [camera.target.x.to_m, camera.target.y.to_m, camera.target.z.to_m].map { |v| v.round(4) },
        fov: camera.fov.round(2),
        viewport: [view.vpwidth, view.vpheight]
      },
      tile_polygons: tile_polygons.length,
      upper_polygons: upper_polygons.length,
      total_tile_area_px2: total_tile_area.round(2),
      total_upper_area_px2: total_upper_area.round(2),
      total_overlap_area_px2: total_overlap_area.round(2),
      overlap_pct_of_smaller: ((100 * total_overlap_area / [total_tile_area, total_upper_area].min) rescue 0).round(2),
      overlapping_pairs: overlapping_pairs,
      boundary_only_pairs: boundary_only_pairs,
      conclusion: nil
    }
    
    # Determine conclusion
    if overlapping_pairs.empty? && boundary_only_pairs.length > 0
      result[:conclusion] = 'BOUNDARY_ONLY_CONTACT'
      result[:conclusion_detail] = 'Faces touch at boundaries but do not overlap in camera projection space'
    elsif overlapping_pairs.length > 0 && result[:overlap_pct_of_smaller] > 5
      result[:conclusion] = 'TRUE_CAMERA_SPACE_OVERLAP'
      result[:conclusion_detail] = "#{overlapping_pairs.length} face pairs have true geometric overlap in camera projection"
    elsif overlapping_pairs.length > 0
      result[:conclusion] = 'MINOR_OVERLAP'
      result[:conclusion_detail] = 'Small overlap detected, likely edge effects'
    else
      result[:conclusion] = 'NO_OVERLAP'
      result[:conclusion_detail] = 'No overlap or boundary contact detected'
    end
    
    puts "\nCONCLUSION: #{result[:conclusion]}"
    puts result[:conclusion_detail]
    
    # Save result
    output_path = File.join(skp_dir, 'camera_projection_audit.json')
    File.open(output_path, 'w') { |f| f.write(JSON.pretty_generate(result)) }
    puts "\n✓ Saved: #{output_path}"
    
    result
  end
end

puts "CameraProjectionAudit loaded."
puts "Run: CameraProjectionAudit.run"
