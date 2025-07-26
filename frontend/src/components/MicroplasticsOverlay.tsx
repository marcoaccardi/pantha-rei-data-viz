import React, { useRef, useMemo, useEffect, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

interface MicroplasticsPoint {
  position: [number, number, number];
  concentration: number;
  confidence: number;
  dataSource: 'real' | 'synthetic';
  date: string;
  concentrationClass: string;
  coordinates: [number, number]; // [lon, lat]
}

interface MicroplasticsOverlayProps {
  visible: boolean;
  onPointHover?: (point: MicroplasticsPoint | null) => void;
  onPointClick?: (point: MicroplasticsPoint) => void;
}

const MicroplasticsOverlay: React.FC<MicroplasticsOverlayProps> = ({
  visible,
  onPointHover,
  onPointClick
}) => {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const { camera, raycaster, pointer } = useThree();
  const [points, setPoints] = useState<MicroplasticsPoint[]>([]);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [zoomScale, setZoomScale] = useState(1);

  // Color mapping for concentration levels
  const getConcentrationColor = (concentrationClass: string): THREE.Color => {
    switch (concentrationClass) {
      case 'Very Low':
        return new THREE.Color(0.7, 0.5, 1.0);  // Light purple
      case 'Low':
        return new THREE.Color(0.5, 0.3, 0.9);  // Medium purple
      case 'Medium':
        return new THREE.Color(1.0, 0.4, 0.8);  // Pink
      case 'High':
        return new THREE.Color(1.0, 0.6, 0.2);  // Orange
      case 'Very High':
        return new THREE.Color(1.0, 0.2, 0.2);  // Red
      default:
        return new THREE.Color(0.5, 0.5, 0.5);  // Gray
    }
  };

  // Point size based on concentration with zoom scaling
  const getPointScale = (concentrationClass: string, dataSource: string, zoomScale: number = 1): number => {
    const baseScale = dataSource === 'real' ? 1.0 : 0.8; // Synthetic points slightly smaller
    
    let concentrationScale: number;
    switch (concentrationClass) {
      case 'Very Low':
        concentrationScale = 0.8;
        break;
      case 'Low':
        concentrationScale = 1.0;
        break;
      case 'Medium':
        concentrationScale = 1.2;
        break;
      case 'High':
        concentrationScale = 1.5;
        break;
      case 'Very High':
        concentrationScale = 2.0;
        break;
      default:
        concentrationScale = 1.0;
    }
    
    // Apply zoom scaling - points get larger when zoomed out, smaller when zoomed in
    return concentrationScale * baseScale * zoomScale;
  };

  // Convert lat/lon to 3D sphere coordinates - positioned above texture layers
  const latLonToVector3 = (lat: number, lon: number, radius: number = 1.004): THREE.Vector3 => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    
    return new THREE.Vector3(x, y, z);
  };

  // Calculate zoom scale based on camera distance
  const calculateZoomScale = (camera: THREE.Camera): number => {
    const distance = camera.position.length();
    // Scale correctly: closer = smaller dots, farther = larger dots (for visibility)
    const minScale = 0.5;  // When zoomed in (close)
    const maxScale = 1.2;  // When zoomed out (far)
    const minDistance = 2.0;
    const maxDistance = 10.0;
    
    const normalizedDistance = Math.max(0, Math.min(1, (distance - minDistance) / (maxDistance - minDistance)));
    return minScale + (normalizedDistance * (maxScale - minScale));
  };

  // Load microplastics data
  useEffect(() => {
    const loadPoints = async () => {
      try {
        setLoading(true);
        console.log('🏭 Loading microplastics points...');
        const response = await fetch('http://localhost:8000/microplastics/points');
        console.log('🏭 Response:', response.status, response.statusText);
        if (!response.ok) {
          const errorText = await response.text();
          console.error('🏭 Error response:', errorText);
          throw new Error(`Failed to load microplastics data: ${response.status} ${response.statusText}`);
        }
        
        const text = await response.text();
        console.log('🏭 Response text preview:', text.substring(0, 200));
        
        let data;
        try {
          data = JSON.parse(text);
        } catch (parseError) {
          console.error('🏭 Failed to parse JSON:', parseError);
          console.error('🏭 Response was:', text);
          throw new Error('Invalid JSON response');
        }
        
        console.log('🏭 Loaded data:', data);
        console.log('🏭 Data type:', data.type);
        console.log('🏭 Features count:', data.features?.length);
        console.log('🏭 Summary:', data.summary);
        
        // Transform GeoJSON features to point objects
        const transformedPoints: MicroplasticsPoint[] = (data.features || []).map((feature: any) => {
          const [lon, lat] = feature.geometry.coordinates;
          const position = latLonToVector3(lat, lon);
          
          return {
            position: [position.x, position.y, position.z],
            concentration: feature.properties.concentration,
            confidence: feature.properties.confidence,
            dataSource: feature.properties.data_source,
            date: feature.properties.date,
            concentrationClass: feature.properties.concentration_class,
            coordinates: [lon, lat]
          };
        });
        
        setPoints(transformedPoints);
        console.log(`Loaded ${transformedPoints.length} microplastics points`);
      } catch (error) {
        console.error('Error loading microplastics data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPoints();
  }, []);

  // Update instanced mesh with zoom scaling
  useEffect(() => {
    if (!meshRef.current || points.length === 0) return;

    const mesh = meshRef.current;
    const tempObject = new THREE.Object3D();

    points.forEach((point, i) => {
      // Set position
      tempObject.position.set(point.position[0], point.position[1], point.position[2]);
      
      // Set scale based on concentration and zoom level
      const scale = getPointScale(point.concentrationClass, point.dataSource, zoomScale) * 0.004;
      tempObject.scale.set(scale, scale, scale);
      
      tempObject.updateMatrix();
      mesh.setMatrixAt(i, tempObject.matrix);
      
      // Set color based on concentration class
      const color = getConcentrationColor(point.concentrationClass);
      
      // Adjust opacity for synthetic data
      if (point.dataSource === 'synthetic') {
        mesh.setColorAt(i, color.multiplyScalar(0.7));
      } else {
        mesh.setColorAt(i, color);
      }
    });

    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [points, zoomScale]);

  // Handle hover interactions, zoom tracking, and visibility culling
  useFrame(() => {
    if (!meshRef.current || !visible || points.length === 0) return;

    // Update zoom scale based on camera distance
    const currentZoomScale = calculateZoomScale(camera);
    if (Math.abs(currentZoomScale - zoomScale) > 0.05) { // Only update if significant change
      setZoomScale(currentZoomScale);
    }

    // Update visibility based on camera position (cull back-facing dots)
    const cameraPosition = camera.position.clone().normalize();
    const mesh = meshRef.current;
    const tempObject = new THREE.Object3D();

    points.forEach((point, i) => {
      // Check if point is facing the camera
      const pointPosition = new THREE.Vector3(point.position[0], point.position[1], point.position[2]);
      const pointNormal = pointPosition.clone().normalize();
      const dotProduct = pointNormal.dot(cameraPosition);
      
      // Hide points on the back side (negative dot product means facing away)
      const isVisible = dotProduct > -0.1; // Small threshold for edge cases
      
      if (isVisible) {
        // Set normal scale
        const scale = getPointScale(point.concentrationClass, point.dataSource, zoomScale) * 0.004;
        tempObject.scale.set(scale, scale, scale);
      } else {
        // Hide by setting scale to zero
        tempObject.scale.set(0, 0, 0);
      }
      
      tempObject.position.set(point.position[0], point.position[1], point.position[2]);
      tempObject.updateMatrix();
      mesh.setMatrixAt(i, tempObject.matrix);
    });

    mesh.instanceMatrix.needsUpdate = true;

    // Cast ray from mouse position
    raycaster.setFromCamera(pointer, camera);
    const intersects = raycaster.intersectObject(meshRef.current);

    if (intersects.length > 0) {
      const instanceId = intersects[0].instanceId;
      if (instanceId !== undefined && instanceId !== hoveredIndex) {
        setHoveredIndex(instanceId);
        if (onPointHover) {
          onPointHover(points[instanceId]);
        }
      }
    } else if (hoveredIndex !== null) {
      setHoveredIndex(null);
      if (onPointHover) {
        onPointHover(null);
      }
    }
  });

  // Create geometry and material - proper depth handling for visibility
  const geometry = useMemo(() => new THREE.SphereGeometry(1, 16, 16), []);
  const material = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0.9,
        depthWrite: true,  // Enable depth writing
        depthTest: true,   // Enable depth testing to hide back-side dots
        side: THREE.FrontSide,
      }),
    []
  );

  if (loading || points.length === 0) {
    return null;
  }

  return (
    <group visible={visible}>
      <instancedMesh
        ref={meshRef}
        args={[geometry, material, points.length]}
        renderOrder={100} // Moderate render order with proper depth testing
        onClick={(event) => {
          if (event.instanceId !== undefined && onPointClick) {
            onPointClick(points[event.instanceId]);
          }
        }}
        onPointerOver={(event) => {
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={(event) => {
          document.body.style.cursor = 'auto';
        }}
      />
    </group>
  );
};

export default MicroplasticsOverlay;