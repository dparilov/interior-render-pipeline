"""
IRP Bundle Validator

Validates bundle against BUNDLE_SPEC v1.1 before rendering.
Catches contract violations early.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np


class ValidationError:
    def __init__(self, severity: str, field: str, message: str):
        self.severity = severity  # "error" or "warning"
        self.field = field
        self.message = message
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.field}: {self.message}"


class BundleValidator:
    """Validates IRP bundle against BUNDLE_SPEC v1.1."""
    
    REQUIRED_ROOT_FIELDS = [
        "version", "scene_id", "created", "base_image", 
        "depth_map", "boundary_mask", "image_size", "camera", 
        "technical_spec", "entities"
    ]
    
    REQUIRED_ENTITY_FIELDS = [
        "pid", "name", "role", "class", "mask", "coverage_pct",
        "prompt", "prompt_source", "critical", "render_mode", "ipadapter_weight"
    ]
    
    VALID_CLASSES = ["surface", "fixture", "opening"]
    VALID_RENDER_MODES = ["regional_ipadapter", "structural_controlnet"]
    
    def __init__(self, bundle_path: Path):
        self.bundle_path = Path(bundle_path)
        self.errors: List[ValidationError] = []
        self.manifest: Optional[dict] = None
    
    def validate(self) -> Tuple[bool, List[ValidationError]]:
        """Run all validations. Returns (is_valid, errors)."""
        self.errors = []
        
        # 1. Check manifest exists and is valid JSON
        if not self._validate_manifest_exists():
            return False, self.errors
        
        # 2. Validate root fields
        self._validate_root_fields()
        
        # 3. Validate file existence
        self._validate_files_exist()
        
        # 4. Validate entities
        self._validate_entities()
        
        # 5. Validate image properties
        self._validate_images()
        
        # 6. Validate technical_spec hash
        self._validate_technical_spec()
        
        # Check if any errors (not warnings)
        has_errors = any(e.severity == "error" for e in self.errors)
        return not has_errors, self.errors
    
    def _add_error(self, field: str, message: str):
        self.errors.append(ValidationError("error", field, message))
    
    def _add_warning(self, field: str, message: str):
        self.errors.append(ValidationError("warning", field, message))
    
    def _validate_manifest_exists(self) -> bool:
        manifest_path = self.bundle_path / "manifest.json"
        if not manifest_path.exists():
            self._add_error("manifest.json", "File not found")
            return False
        
        try:
            with open(manifest_path) as f:
                self.manifest = json.load(f)
            return True
        except json.JSONDecodeError as e:
            self._add_error("manifest.json", f"Invalid JSON: {e}")
            return False
    
    def _validate_root_fields(self):
        for field in self.REQUIRED_ROOT_FIELDS:
            if field not in self.manifest:
                self._add_error(f"manifest.{field}", "Required field missing")
        
        # Validate version
        if self.manifest.get("version") not in ["1.0", "1.1"]:
            self._add_warning("manifest.version", f"Unknown version: {self.manifest.get('version')}")
        
        # Validate image_size
        img_size = self.manifest.get("image_size", {})
        if not isinstance(img_size.get("width"), int) or not isinstance(img_size.get("height"), int):
            self._add_error("manifest.image_size", "width and height must be integers")
        
        # Validate camera
        camera = self.manifest.get("camera", {})
        for field in ["eye", "target", "up", "fov"]:
            if field not in camera:
                self._add_error(f"manifest.camera.{field}", "Required field missing")
    
    def _validate_files_exist(self):
        # Check required files
        for field in ["base_image", "depth_map", "boundary_mask"]:
            path = self.manifest.get(field)
            if path and not (self.bundle_path / path).exists():
                self._add_error(f"manifest.{field}", f"File not found: {path}")
        
        # Check technical_spec file
        tech_spec = self.manifest.get("technical_spec", {})
        if tech_spec.get("path"):
            if not (self.bundle_path / tech_spec["path"]).exists():
                self._add_error("manifest.technical_spec.path", f"File not found: {tech_spec['path']}")
    
    def _validate_entities(self):
        entities = self.manifest.get("entities", [])
        if not entities:
            self._add_error("manifest.entities", "No entities defined")
            return
        
        seen_pids = set()
        seen_names = set()
        total_coverage = 0.0
        
        for i, entity in enumerate(entities):
            prefix = f"manifest.entities[{i}]"
            
            # Check required fields
            for field in self.REQUIRED_ENTITY_FIELDS:
                if field not in entity:
                    self._add_error(f"{prefix}.{field}", "Required field missing")
            
            # Validate PID uniqueness
            pid = entity.get("pid")
            if pid in seen_pids:
                self._add_error(f"{prefix}.pid", f"Duplicate PID: {pid}")
            seen_pids.add(pid)
            
            # Validate name uniqueness
            name = entity.get("name")
            if name in seen_names:
                self._add_error(f"{prefix}.name", f"Duplicate name: {name}")
            seen_names.add(name)
            
            # Validate class
            entity_class = entity.get("class")
            if entity_class not in self.VALID_CLASSES:
                self._add_error(f"{prefix}.class", f"Invalid class: {entity_class}")
            
            # Validate render_mode
            render_mode = entity.get("render_mode")
            if render_mode not in self.VALID_RENDER_MODES:
                self._add_error(f"{prefix}.render_mode", f"Invalid render_mode: {render_mode}")
            
            # Check mask exists
            mask_path = entity.get("mask")
            if mask_path and not (self.bundle_path / mask_path).exists():
                self._add_error(f"{prefix}.mask", f"File not found: {mask_path}")
            
            # Check reference exists (required for non-opening)
            reference = entity.get("reference")
            if entity_class != "opening" and entity.get("critical"):
                if not reference:
                    self._add_error(f"{prefix}.reference", "Critical entity must have reference")
                elif not (self.bundle_path / reference).exists():
                    self._add_error(f"{prefix}.reference", f"File not found: {reference}")
            
            # Validate weight rules
            weight = entity.get("ipadapter_weight", 0)
            if entity_class == "opening" and weight != 0:
                self._add_warning(f"{prefix}.ipadapter_weight", "Opening should have weight 0")
            
            # Track coverage
            coverage = entity.get("coverage_pct", 0)
            total_coverage += coverage
        
        # Check total coverage
        if total_coverage > 100:
            self._add_warning("manifest.entities", f"Total coverage {total_coverage:.1f}% > 100%")
    
    def _validate_images(self):
        """Validate image properties."""
        # Check boundary_mask is binary
        boundary_path = self.bundle_path / self.manifest.get("boundary_mask", "")
        if boundary_path.exists():
            try:
                img = Image.open(boundary_path).convert("L")
                arr = np.array(img)
                unique = np.unique(arr)
                non_binary = len(unique) > 2 or (len(unique) == 2 and set(unique) != {0, 255})
                if non_binary:
                    self._add_error("boundary_mask", f"Must be binary (0 and 255 only), found {len(unique)} unique values")
            except Exception as e:
                self._add_error("boundary_mask", f"Cannot read image: {e}")
        
        # Check depth has gradient
        depth_path = self.bundle_path / self.manifest.get("depth_map", "")
        if depth_path.exists():
            try:
                img = Image.open(depth_path).convert("L")
                arr = np.array(img)
                unique = np.unique(arr)
                if len(unique) < 10:
                    self._add_warning("depth_map", f"Low gradient diversity: only {len(unique)} unique values")
            except Exception as e:
                self._add_error("depth_map", f"Cannot read image: {e}")
        
        # Check entity masks are binary and calculate actual coverage
        total_pixels = None
        for entity in self.manifest.get("entities", []):
            mask_path = self.bundle_path / entity.get("mask", "")
            if mask_path.exists():
                try:
                    img = Image.open(mask_path).convert("L")
                    arr = np.array(img)
                    
                    if total_pixels is None:
                        total_pixels = arr.size
                    
                    unique = np.unique(arr)
                    non_binary = len(unique) > 2 or (len(unique) == 2 and set(unique) != {0, 255})
                    if non_binary:
                        self._add_warning(f"masks/{entity['name']}", f"Mask should be binary, found {len(unique)} values")
                    
                    # Calculate actual coverage
                    white_pixels = np.sum(arr == 255)
                    actual_coverage = (white_pixels / total_pixels) * 100
                    declared_coverage = entity.get("coverage_pct", 0)
                    
                    # Store for later use
                    entity["_actual_coverage_pct"] = round(actual_coverage, 2)
                    
                    # Warn if declared coverage differs significantly
                    if abs(actual_coverage - declared_coverage) > 5:
                        self._add_warning(
                            f"masks/{entity['name']}", 
                            f"coverage_pct mismatch: declared {declared_coverage}%, actual {actual_coverage:.1f}%"
                        )
                except Exception as e:
                    self._add_error(f"masks/{entity['name']}", f"Cannot read mask: {e}")
    
    def _validate_technical_spec(self):
        """Validate technical_spec hash matches file."""
        tech_spec = self.manifest.get("technical_spec", {})
        path = tech_spec.get("path")
        declared_hash = tech_spec.get("hash", "")
        
        if not path:
            return
        
        full_path = self.bundle_path / path
        if not full_path.exists():
            return  # Already reported in _validate_files_exist
        
        # Calculate actual hash
        with open(full_path, "rb") as f:
            actual_hash = f"sha256:{hashlib.sha256(f.read()).hexdigest()}"
        
        if declared_hash and not actual_hash.startswith(declared_hash.split(":")[0]):
            # Just check prefix format
            if ":" in declared_hash:
                prefix = declared_hash.split(":")[1][:16]
                actual_prefix = actual_hash.split(":")[1][:16]
                if prefix != actual_prefix:
                    self._add_error("manifest.technical_spec.hash", 
                                   f"Hash mismatch: declared {prefix}..., actual {actual_prefix}...")


def validate_bundle(bundle_path: Path) -> Tuple[bool, List[str]]:
    """Convenience function to validate a bundle.
    
    Returns (is_valid, list of error messages).
    """
    validator = BundleValidator(bundle_path)
    is_valid, errors = validator.validate()
    return is_valid, [str(e) for e in errors]


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validate.py <bundle_path>")
        sys.exit(1)
    
    bundle_path = Path(sys.argv[1])
    is_valid, errors = validate_bundle(bundle_path)
    
    for error in errors:
        print(error)
    
    if is_valid:
        print("\n✅ Bundle is valid")
        sys.exit(0)
    else:
        print("\n❌ Bundle validation failed")
        sys.exit(1)
