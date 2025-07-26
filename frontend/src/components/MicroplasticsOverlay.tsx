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

  // Point size based on concentration
  const getPointScale = (concentrationClass: string, dataSource: string): number => {
    const baseScale = dataSource === 'real' ? 1.0 : 0.8; // Synthetic points slightly smaller
    
    switch (concentrationClass) {
      case 'Very Low':
        return 0.8 * baseScale;
      case 'Low':
        return 1.0 * baseScale;
      case 'Medium':
        return 1.2 * baseScale;
      case 'High':
        return 1.5 * baseScale;
      case 'Very High':
        return 2.0 * baseScale;
      default:
        return 1.0 * baseScale;
    }
  };

  // Convert lat/lon to 3D sphere coordinates
  const latLonToVector3 = (lat: number, lon: number, radius: number = 1.003): THREE.Vector3 => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    
    return new THREE.Vector3(x, y, z);
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

  // Update instanced mesh
  useEffect(() => {
    if (!meshRef.current || points.length === 0) return;

    const mesh = meshRef.current;
    const tempObject = new THREE.Object3D();
    const tempColor = new THREE.Color();

    points.forEach((point, i) => {
      // Set position
      tempObject.position.set(point.position[0], point.position[1], point.position[2]);
      
      // Set scale based on concentration
      const scale = getPointScale(point.concentrationClass, point.dataSource) * 0.01;
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
  }, [points]);

  // Handle hover interactions
  useFrame(() => {
    if (!meshRef.current || !visible || points.length === 0) return;

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

  // Create geometry and material
  const geometry = useMemo(() => new THREE.SphereGeometry(1, 16, 16), []);
  const material = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0.8,
        depthWrite: false,
        depthTest: true,
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