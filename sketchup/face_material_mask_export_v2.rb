# Face Material Mask Export v2 for IRP
# Config-driven, camera-validated face projection
#
# Run in SketchUp Ruby Console:
#   load '/path/to/face_material_mask_export_v2.rb'
#   FaceMaterialMaskExportV2.export_from_config('/path/to/face_projection_config.json')

require 'sketchup'
require 'json'
require 'fileutils'

module FaceMaterialMaskExportV2
  VERSION = '2.0'
  
  def self.model
    Sketchup.active_model
  end
  
  def self.view
    model.active_view
  end
  
  def self.camera
    view.camera
  end
  
  # Load and validate config
  def self.load_config(config_path)
    unless File.exist?(config_path)
      raise "Config file not found: #{config_path}"
    end
    JSON.parse(File.read(config_path))
  end
  
  # Validate camera matches reference
  def self.validate_camera(config)
    ref = config['camera_reference']
    tol = ref['tolerance']
    
    current_eye = [camera.eye.x.to_m, camera.eye.y.to_m, camera.eye.z.to_m]
    current_target = [camera.target.x.to_m, camera.target.y.to_m, camera.target.z.to_m]
    current_up = [camera.up.x, camera.up.y, camera.up.z]
    current_fov = camera.fov
    
    errors = []
    
    # Check eye position
    eye_dist = Math.sqrt(
      (current_eye[0] - ref['eye'][0])**2 +
      (current_eye[1] - ref['eye'][1])**2 +
      (current_eye[2] - ref['eye'][2])**2
    )
    if eye_dist > tol['position']
      errors << "Camera eye mismatch: distance=#{eye_dist.round(4)}m (tolerance=#{tol['position']}m)"
    end
    
    # Check target position
    target_dist = Math.sqrt(
      (current_target[0] - ref['target'][0])**2 +
      (current_target[1] - ref['target'][1])**2 +
      (current_target[2] - ref['target'][2])**2
    )
    if target_dist > tol['position']
      errors << "Camera target mismatch: distance=#{target_dist.round(4)}m (tolerance=#{tol['position']}m)"
    end
    
    # Check FOV
    fov_diff = (current_fov - ref['fov']).abs
    if fov_diff > tol['fov']
      errors << "Camera FOV mismatch: current=#{current_fov.round(2)}, expected=#{ref['fov']} (tolerance=#{tol['fov']})"
    end
    
    # Check up vector
    up_dist = Math.sqrt(
      (current_up[0] - ref['up'][0])**2 +
      (current_up[1] - ref['up'][1])**2 +
      (current_up[2] - ref['up'][2])**2
    )
    if up_dist > tol['direction']
      errors << "Camera up vector mismatch: distance=#{up_dist.round(6)} (tolerance=#{tol['direction']})"
    end
    
    {
      valid: errors.empty?,
      errors: errors,
      current: {
        eye: current_eye.map { |v| v.round(4) },
        target: current_target.map { |v| v.round(4) },
        up: current_up.map { |v| v.round(6) },
        fov: current_fov.round(2)
      },
      reference: {
        eye: ref['eye'],
        target: ref['target'],
        up: ref['up'],
        fov: ref['fov']
      }
    }
  end
  
  # Find entity by PID
  def self.find_entity(pid)
    model.find_entity_by_persistent_id(pid)
  end
  
  # Get inner entities of group/component
  def self.get_inner_entities(entity)
    case entity
      when Sketchup::Group then entity.entities
      when Sketchup::ComponentInstance then entity.definition.entities
      else nil
    end
  end
  
  # Export single material region mask
  def self.export_material_mask(entity, material_name, output_path, resolution)
    inner = get_inner_entities(entity)
    return nil unless inner
    
    white = Sketchup::Color.new(255, 255, 255)
    black = Sketchup::Color.new(0, 0, 0)
    
    model.start_operation('Export Material Mask', true)
    
    result = nil
    begin
      # Hide everything
      model.entities.each { |e| e.hidden = true if e.respond_to?(:hidden=) }
      entity.hidden = false
      
      # Store original materials
      original_materials = {}
      target_faces = []
      
      inner.grep(Sketchup::Face).each do |face|
        original_materials[face] = {
          front: face.material,
          back: face.back_material
        }
        
        mat = face.material || face.back_material || entity.material
        mat_name = mat ? mat.display_name : 'none'
        
        if mat_name == material_name
          face.material = white
          face.back_material = white
          target_faces << face
        else
          face.material = black
          face.back_material = black
        end
      end
      
      # Calculate area
      total_area = target_faces.sum { |f| f.area * 0.00064516 }
      
      # Export
      view.refresh
      sleep(0.2)
      view.write_image(output_path, resolution[0], resolution[1], true)
      
      result = {
        material: material_name,
        faces: target_faces.length,
        area_m2: total_area.round(4),
        path: output_path
      }
      
      # Restore materials
      original_materials.each do |face, mats|
        face.material = mats[:front]
        face.back_material = mats[:back]
      end
      
      # Restore visibility
      model.entities.each { |e| e.hidden = false if e.respond_to?(:hidden=) }
      
    ensure
      model.abort_operation
    end
    
    result
  end
  
  # Get current scene name
  def self.current_scene_name
    page = model.pages.selected_page
    page ? page.name : 'Default'
  end
  
  # Main export function
  def self.export_from_config(config_path)
    puts "=" * 70
    puts "FACE MATERIAL MASK EXPORT v#{VERSION}"
    puts "Config: #{config_path}"
    puts "=" * 70
    
    # Load config
    config = load_config(config_path)
    puts "\nScene: #{config['scene_id']}"
    
    # Validate camera
    puts "\n--- CAMERA VALIDATION ---"
    cam_result = validate_camera(config)
    
    # Check scene/page
    current_scene = current_scene_name
    expected_scene = config['camera_reference']['scene_name'] rescue nil
    if expected_scene && current_scene != expected_scene
      cam_result[:errors] << "Scene mismatch: current='#{current_scene}', expected='#{expected_scene}'"
      cam_result[:valid] = false
    end
    
    if cam_result[:valid]
      puts "✓ Camera matches reference"
      puts "✓ Scene: #{current_scene}"
    else
      puts "✗ Camera validation FAILED:"
      cam_result[:errors].each { |e| puts "  - #{e}" }
      puts "\nCurrent camera:"
      puts "  Eye: #{cam_result[:current][:eye]}"
      puts "  Target: #{cam_result[:current][:target]}"
      puts "  FOV: #{cam_result[:current][:fov]}"
      puts "\nExpected camera:"
      puts "  Eye: #{cam_result[:reference][:eye]}"
      puts "  Target: #{cam_result[:reference][:target]}"
      puts "  FOV: #{cam_result[:reference][:fov]}"
      puts "\n⛔ ABORTING: Camera must match canonical view for mask export"
      return nil
    end
    
    # Find target entity
    target_pid = config['target_entity']['pid']
    entity = find_entity(target_pid)
    
    unless entity
      puts "✗ Target entity not found: pid=#{target_pid}"
      return nil
    end
    puts "✓ Found target entity: pid=#{target_pid}"
    
    # Determine output directory
    config_dir = File.dirname(config_path)
    output_dir = config_dir
    
    # Export each material region
    puts "\n--- EXPORTING MASKS ---"
    resolution = [config['resolution']['width'], config['resolution']['height']]
    
    exports = []
    config['materials_to_entities'].each do |mat_name, mat_config|
      entity_name = mat_config['entity_name']
      output_path = File.join(output_dir, config['output_masks'][entity_name])
      
      puts "\nExporting: #{entity_name}"
      puts "  Material: #{mat_name}"
      puts "  Output: #{output_path}"
      
      result = export_material_mask(entity, mat_name, output_path, resolution)
      
      if result
        puts "  ✓ Exported: #{result[:faces]} faces, #{result[:area_m2]} m²"
        
        exports << {
          entity_name: entity_name,
          role: mat_config['role'],
          source_material: mat_name,
          material_face_count: result[:faces],
          material_area_m2: result[:area_m2],
          mask_path: output_path,
          has_reference: mat_config['has_reference'],
          reference_path: mat_config['reference_path']
        }
      else
        puts "  ✗ Export failed"
      end
    end
    
    # Generate comprehensive metadata
    puts "\n--- GENERATING METADATA ---"
    
    metadata = {
      version: VERSION,
      export_timestamp: Time.now.iso8601,
      config_file: File.basename(config_path),
      scene_id: config['scene_id'],
      scene_name: current_scene_name,
      
      target_entity: {
        pid: target_pid,
        name: config['target_entity']['name']
      },
      
      camera: {
        eye: cam_result[:current][:eye],
        target: cam_result[:current][:target],
        up: cam_result[:current][:up],
        fov: cam_result[:current][:fov],
        validated: true
      },
      
      resolution: {
        width: resolution[0],
        height: resolution[1]
      },
      
      mask_source: 'skp_face_projection',
      mask_derivation: 'direct_face_render',
      
      exports: exports,
      
      deprecation: {
        old_method: 'walls.png Y-split',
        status: 'DEPRECATED',
        reason: 'Replaced by direct face projection from SKP material regions'
      }
    }
    
    metadata_path = File.join(output_dir, 'face_projection_metadata.json')
    File.open(metadata_path, 'w') { |f| f.write(JSON.pretty_generate(metadata)) }
    puts "✓ Metadata saved: #{metadata_path}"
    
    puts "\n" + "=" * 70
    puts "EXPORT COMPLETE"
    puts "  Masks: #{exports.length}"
    puts "  Output: #{output_dir}"
    puts "=" * 70
    
    metadata
  end
end

puts "FaceMaterialMaskExportV2 loaded."
puts "Usage: FaceMaterialMaskExportV2.export_from_config('/path/to/face_projection_config.json')"
