# Camera Projection Audit v3 for IRP
require 'sketchup'
require 'json'

module CamProjAuditV3
  VERSION = '3.0'
  TARGET_PID = 36696
  
  MATERIAL_GROUPS = {
    'Материал1' => 'walls_tile',
    '0131_Серебристый' => 'walls_upper'
  }
  
  def self.model; Sketchup.active_model; end
  def self.view; model.active_view; end
  def self.camera; view.camera; end
  def self.skp_dir; File.dirname(model.path); end
  def self.find_entity(pid); model.find_entity_by_persistent_id(pid); end
  
  def self.get_inner_entities(entity)
    return entity.entities if entity.is_a?(Sketchup::Group)
    return entity.definition.entities if entity.is_a?(Sketchup::ComponentInstance)
    nil
  end
  
  def self.project_point(point3d)
    screen_pt = view.screen_coords(point3d)
    [screen_pt.x, screen_pt.y]
  end
  
  def self.get_projected_polygon(face, transformation)
    vertices = face.vertices.map { |v| v.position }
    vertices = vertices.map { |v| transformation * v } if transformation
    vertices.map { |v| project_point(v) }
  end
  
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
  
  def self.polygon_bounds(vertices)
    xs = vertices.map { |v| v[0] }
    ys = vertices.map { |v| v[1] }
    { min_x: xs.min, max_x: xs.max, min_y: ys.min, max_y: ys.max }
  end
  
  def self.bounds_overlap?(b1, b2)
    return false if b1[:max_x] < b2[:min_x]
    return false if b2[:max_x] < b1[:min_x]
    return false if b1[:max_y] < b2[:min_y]
    return false if b2[:max_y] < b1[:min_y]
    true
  end
  
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
  
  def self.estimate_overlap(poly1, poly2, samples_per_side)
    b1 = polygon_bounds(poly1)
    b2 = polygon_bounds(poly2)
    
    unless bounds_overlap?(b1, b2)
      return { overlap_area: 0, overlap_ratio: 0, samples_checked: 0, samples_overlapping: 0 }
    end
    
    min_x = [b1[:min_x], b2[:min_x]].max
    max_x = [b1[:max_x], b2[:max_x]].min
    min_y = [b1[:min_y], b2[:min_y]].max
    max_y = [b1[:max_y], b2[:max_y]].min
    
    if min_x >= max_x
      return { overlap_area: 0, overlap_ratio: 0, samples_checked: 0, samples_overlapping: 0 }
    end
    if min_y >= max_y
      return { overlap_area: 0, overlap_ratio: 0, samples_checked: 0, samples_overlapping: 0 }
    end
    
    step_x = (max_x - min_x) / samples_per_side.to_f
    step_y = (max_y - min_y) / samples_per_side.to_f
    
    overlap_count = 0
    total_samples = 0
    
    (0..samples_per_side).each do |i|
      (0..samples_per_side).each do |j|
        x = min_x + i * step_x
        y = min_y + j * step_y
        point = [x, y]
        
        in1 = point_in_polygon?(point, poly1)
        in2 = point_in_polygon?(point, poly2)
        
        overlap_count += 1 if in1 && in2
        total_samples += 1
      end
    end
    
    sample_area = step_x * step_y
    overlap_area = overlap_count * sample_area
    
    area1 = polygon_area(poly1)
    area2 = polygon_area(poly2)
    min_area = [area1, area2].min
    
    ratio = 0
    ratio = overlap_area / min_area if min_area > 0
    
    {
      overlap_area: overlap_area.round(2),
      overlap_ratio: ratio.round(4),
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
    
    puts "\n--- CAMERA INFO ---"
    puts "Eye: (#{camera.eye.x.to_m.round(3)}, #{camera.eye.y.to_m.round(3)}, #{camera.eye.z.to_m.round(3)})"
    puts "Target: (#{camera.target.x.to_m.round(3)}, #{camera.target.y.to_m.round(3)}, #{camera.target.z.to_m.round(3)})"
    puts "FOV: #{camera.fov.round(2)}"
    puts "View size: #{view.vpwidth} x #{view.vpheight}"
    
    entity = find_entity(TARGET_PID)
    unless entity
      puts "ERROR: Entity #{TARGET_PID} not found"
      return nil
    end
    
    inner = get_inner_entities(entity)
    transformation = entity.transformation
    
    faces_by_material = {}
    inner.grep(Sketchup::Face).each do |face|
      mat = face.material
      mat = face.back_material if mat.nil?
      mat = entity.material if mat.nil?
      mat_name = mat ? mat.display_name : 'none'
      faces_by_material[mat_name] = [] unless faces_by_material[mat_name]
      faces_by_material[mat_name] << face
    end
    
    puts "\n--- FACES BY MATERIAL ---"
    faces_by_material.each do |mat, faces|
      gn = MATERIAL_GROUPS[mat]
      gn = 'other' if gn.nil?
      puts "  #{mat} (#{gn}): #{faces.length} faces"
    end
    
    puts "\n--- PROJECTING FACES ---"
    
    tile_mat = 'Материал1'
    upper_mat = '0131_Серебристый'
    
    tile_faces = faces_by_material[tile_mat]
    tile_faces = [] if tile_faces.nil?
    upper_faces = faces_by_material[upper_mat]
    upper_faces = [] if upper_faces.nil?
    
    tile_polygons = []
    tile_faces.each_with_index do |face, i|
      poly = get_projected_polygon(face, transformation)
      area = polygon_area(poly)
      bounds = polygon_bounds(poly)
      tile_polygons << { index: i, vertices: poly, area: area.round(2), bounds: bounds }
      puts "  Tile face #{i}: area=#{area.round(0)} px2"
    end
    
    upper_polygons = []
    upper_faces.each_with_index do |face, i|
      poly = get_projected_polygon(face, transformation)
      area = polygon_area(poly)
      bounds = polygon_bounds(poly)
      upper_polygons << { index: i, vertices: poly, area: area.round(2), bounds: bounds }
      puts "  Upper face #{i}: area=#{area.round(0)} px2"
    end
    
    puts "\n--- CHECKING PAIRWISE OVERLAP ---"
    
    overlapping_pairs = []
    boundary_only_pairs = []
    
    tile_polygons.each do |tp|
      upper_polygons.each do |up|
        if bounds_overlap?(tp[:bounds], up[:bounds])
          result = estimate_overlap(tp[:vertices], up[:vertices], 30)
          
          if result[:samples_overlapping] > 0
            pair_info = {
              tile_face: tp[:index],
              upper_face: up[:index],
              overlap_samples: result[:samples_overlapping],
              total_samples: result[:samples_checked],
              overlap_area_px2: result[:overlap_area],
              overlap_ratio: result[:overlap_ratio]
            }
            
            ratio = result[:overlap_ratio]
            ratio = 0 if ratio.nil?
            
            if ratio > 0.01
              overlapping_pairs << pair_info
              puts "  OVERLAP: tile[#{tp[:index]}] - upper[#{up[:index]}]: ratio=#{ratio.round(4)}"
            else
              boundary_only_pairs << pair_info
              puts "  BOUNDARY: tile[#{tp[:index]}] - upper[#{up[:index]}]: #{result[:samples_overlapping]} samples"
            end
          end
        end
      end
    end
    
    puts "\n" + "=" * 70
    puts "OVERLAP SUMMARY"
    puts "=" * 70
    puts "True overlapping pairs: #{overlapping_pairs.length}"
    puts "Boundary contact pairs: #{boundary_only_pairs.length}"
    
    total_overlap_area = 0
    overlapping_pairs.each { |p| total_overlap_area += p[:overlap_area_px2] }
    
    total_tile_area = 0
    tile_polygons.each { |p| total_tile_area += p[:area] }
    
    total_upper_area = 0
    upper_polygons.each { |p| total_upper_area += p[:area] }
    
    puts "\nTotal projected areas:"
    puts "  Tile: #{total_tile_area.round(0)} px2"
    puts "  Upper: #{total_upper_area.round(0)} px2"
    puts "  Overlap: #{total_overlap_area.round(0)} px2"
    
    smaller = [total_tile_area, total_upper_area].min
    overlap_pct = 0
    overlap_pct = 100 * total_overlap_area / smaller if smaller > 0
    puts "  Overlap pct: #{overlap_pct.round(2)}%"
    
    conclusion = 'NO_OVERLAP'
    conclusion_detail = 'No overlap detected'
    
    if overlapping_pairs.empty? && boundary_only_pairs.length > 0
      conclusion = 'BOUNDARY_ONLY_CONTACT'
      conclusion_detail = 'Faces touch at boundaries but do not overlap'
    elsif overlapping_pairs.length > 0 && overlap_pct > 5
      conclusion = 'TRUE_CAMERA_SPACE_OVERLAP'
      conclusion_detail = "#{overlapping_pairs.length} face pairs have true overlap"
    elsif overlapping_pairs.length > 0
      conclusion = 'MINOR_OVERLAP'
      conclusion_detail = 'Small overlap, likely edge effects'
    end
    
    puts "\nCONCLUSION: #{conclusion}"
    puts conclusion_detail
    
    result = {
      version: VERSION,
      audit_date: Time.now.iso8601,
      camera: {
        eye: [camera.eye.x.to_m.round(4), camera.eye.y.to_m.round(4), camera.eye.z.to_m.round(4)],
        target: [camera.target.x.to_m.round(4), camera.target.y.to_m.round(4), camera.target.z.to_m.round(4)],
        fov: camera.fov.round(2),
        viewport: [view.vpwidth, view.vpheight]
      },
      tile_polygons: tile_polygons.length,
      upper_polygons: upper_polygons.length,
      total_tile_area_px2: total_tile_area.round(2),
      total_upper_area_px2: total_upper_area.round(2),
      total_overlap_area_px2: total_overlap_area.round(2),
      overlap_pct_of_smaller: overlap_pct.round(2),
      overlapping_pairs_count: overlapping_pairs.length,
      boundary_pairs_count: boundary_only_pairs.length,
      overlapping_pairs: overlapping_pairs,
      conclusion: conclusion,
      conclusion_detail: conclusion_detail
    }
    
    output_path = File.join(skp_dir, 'camera_projection_audit.json')
    File.open(output_path, 'w') { |f| f.write(JSON.pretty_generate(result)) }
    puts "\nSaved: #{output_path}"
    
    result
  end
end

puts "CamProjAuditV3 loaded. Run: CamProjAuditV3.run"
