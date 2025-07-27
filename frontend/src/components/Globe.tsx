import React, { useRef, useState, useCallback } from 'react';
import { useFrame, useThree, useLoader } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Mesh, TextureLoader } from 'three';
import Scene from './Scene';
import MicroplasticsOverlay from './MicroplasticsOverlay';
import { useGlobeCamera } from '../hooks/useGlobeCamera';
import { useTextureLoader } from '../hooks/useTextureLoader';
import type { GlobeProps, Coordinates } from '../utils/types';

const LoadingIndicator: React.FC = () => {
  return <group />; // Empty - no visual elements
};

const PositionMarker: React.FC<{ coordinates: Coordinates }> = ({ coordinates }) => {
  const markerRef = useRef<Mesh>(null);
  
  const position = React.useMemo(() => {
    const phi = (90 - coordinates.lat) * (Math.PI / 180);
    const theta = (coordinates.lng + 180) * (Math.PI / 180);
    const radius = 1.005; // Very slightly above the globe surface
    
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = (radius * Math.sin(phi) * Math.sin(theta));
    const y = (radius * Math.cos(phi));
    
    return [x, y, z] as [number, number, number];
  }, [coordinates]);

  useFrame((state) => {
    if (markerRef.current) {
      // Pulsating effect
      const scale = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.2;
      markerRef.current.scale.setScalar(scale);
    }
  });

  return (
    <group position={position}>
      {/* Red dot marker */}
      <mesh ref={markerRef}>
        <sphereGeometry args={[0.02, 16, 16]} />
        <meshBasicMaterial color="#ff0000" />
      </mesh>
      
      {/* Glow effect for marker */}
      <mesh>
        <sphereGeometry args={[0.025, 16, 16]} />
        <meshBasicMaterial 
          color="#ff0000" 
          transparent 
          opacity={0.3}
        />
      </mesh>
      
    </group>
  );
};

const GlobeMesh: React.FC<{
  isLoading: boolean;
  selectedCoordinates?: Coordinates;
  showDataOverlay?: boolean;
  dataCategory?: string;
  showMicroplastics?: boolean;
  onMicroplasticsPointHover?: (point: any) => void;
  onMicroplasticsPointClick?: (point: any) => void;
}> = ({ isLoading, selectedCoordinates, showDataOverlay = false, dataCategory = 'sst', showMicroplastics = false, onMicroplasticsPointHover, onMicroplasticsPointClick }) => {
  const meshRef = useRef<Mesh>(null);
  const sstMeshRef = useRef<Mesh>(null);

  // Load textures using the texture loader hook - pass external category
  const { earthTexture, dataTexture, selectedCategory } = useTextureLoader(dataCategory);

  // Debug: Log when dataTexture changes
  React.useEffect(() => {
    console.log(`🌍 Globe received dataTexture for category: ${selectedCategory}`);
    console.log(`🌍 DataTexture object:`, dataTexture);
  }, [dataTexture, selectedCategory]);

  // Remove auto-rotation - globe should only rotate with user interaction

  return (
    <group>
      {/* NASA Earth Base Layer */}
      <mesh
        ref={meshRef}
      >
        <sphereGeometry args={[1, 360, 180]} />
        <meshStandardMaterial 
          map={earthTexture} 
          transparent
          opacity={0.7}
        />
      </mesh>
      
      {/* Data Overlay Layer */}
      {showDataOverlay && (
        <mesh ref={sstMeshRef}>
          <sphereGeometry args={[1.001, 360, 180]} />
          <meshStandardMaterial
            map={dataTexture}
            transparent
            opacity={0.9}
          />
        </mesh>
      )}
      
      {/* Position marker */}
      {selectedCoordinates && (
        <PositionMarker coordinates={selectedCoordinates} />
      )}
      
      {/* Microplastics overlay - renders above all other layers */}
      <MicroplasticsOverlay
        visible={showMicroplastics}
        onPointHover={onMicroplasticsPointHover}
        onPointClick={onMicroplasticsPointClick}
      />
      
      {isLoading && <LoadingIndicator />}
    </group>
  );
};

const Globe: React.FC<GlobeProps> = ({ 
  coordinates, 
  onLocationChange, 
  isLoading = false,
  showDataOverlay = false,
  dataCategory = 'sst',
  showSSTOverlay = false, // Legacy support
  onZoomFunctionsReady,
  showMicroplastics = false,
  onMicroplasticsPointHover,
  onMicroplasticsPointClick
}) => {
  const [selectedCoordinates, setSelectedCoordinates] = useState<Coordinates | undefined>(coordinates);
  const { animateToCoordinates, orbitControlsRef, resetView, zoomIn, zoomOut } = useGlobeCamera();


  // Animate to coordinates when they change externally
  React.useEffect(() => {
    if (coordinates) {
      setSelectedCoordinates(coordinates);
      animateToCoordinates(coordinates);
    }
  }, [coordinates, animateToCoordinates]);

  // Expose zoom functions to parent component
  React.useEffect(() => {
    if (onZoomFunctionsReady) {
      onZoomFunctionsReady(zoomIn, zoomOut);
    }
  }, [zoomIn, zoomOut, onZoomFunctionsReady]);

  return (
    <Scene>
      <OrbitControls
        ref={orbitControlsRef}
        enablePan={false}
        enableZoom={true}
        enableRotate={true}
        minDistance={1.5}
        maxDistance={10}
        rotateSpeed={0.8}
        zoomSpeed={1.0}
        target={[0, 0, 0]}
        enableDamping={true}
        dampingFactor={0.05}
      />
      
      <GlobeMesh 
        isLoading={isLoading}
        selectedCoordinates={selectedCoordinates}
        showDataOverlay={showDataOverlay || showSSTOverlay} // Support legacy prop
        dataCategory={dataCategory}
        showMicroplastics={showMicroplastics}
        onMicroplasticsPointHover={onMicroplasticsPointHover}
        onMicroplasticsPointClick={onMicroplasticsPointClick}
      />
    </Scene>
  );
};

export default Globe;