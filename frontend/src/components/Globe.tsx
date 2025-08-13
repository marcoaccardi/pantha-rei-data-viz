import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useFrame, useThree, useLoader } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Mesh, TextureLoader } from 'three';
import * as THREE from 'three';
import Scene from './Scene';
import MicroplasticsOverlay from './MicroplasticsOverlay';
import { useGlobeCamera } from '../hooks/useGlobeCamera';
import { useAnimationController } from '../hooks/useAnimationController';
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
  selectedDate?: string;
  showMicroplastics?: boolean;
  onMicroplasticsPointHover?: (point: any) => void;
  onMicroplasticsPointClick?: (point: any) => void;
  onSstTextureLoaded?: () => void;
}> = ({ isLoading, selectedCoordinates, showDataOverlay = false, dataCategory = 'sst', selectedDate, showMicroplastics = false, onMicroplasticsPointHover, onMicroplasticsPointClick, onSstTextureLoaded }) => {
  const meshRef = useRef<Mesh>(null);
  const sstMeshRef = useRef<Mesh>(null);

  // Load earth texture directly using useLoader
  const earthTexture = useLoader(TextureLoader, 'http://localhost:8000/textures/earth/nasa_world_topo_bathy.jpg');
  
  // Load SST texture directly based on date
  const sstTextureUrl = React.useMemo(() => {
    const date = selectedDate || new Date().toISOString().split('T')[0];
    return `http://localhost:8000/textures/sst?date=${date}`;
  }, [selectedDate]);
  
  const [sstTexture, setSstTexture] = useState<THREE.Texture | null>(null);
  const [isSstLoading, setIsSstLoading] = useState<boolean>(false);
  
  // Load SST texture when URL changes
  React.useEffect(() => {
    setIsSstLoading(true);
    const loader = new TextureLoader();
    loader.load(
      sstTextureUrl,
      (texture) => {
        texture.flipY = true;
        setSstTexture(texture);
        setIsSstLoading(false);
        // Notify parent that SST texture is loaded
        if (onSstTextureLoaded) {
          onSstTextureLoaded();
        }
      },
      undefined,
      (error) => {
        console.error('Error loading SST texture:', error);
        setIsSstLoading(false);
      }
    );
  }, [sstTextureUrl, onSstTextureLoaded]);
  
  // Configure earth texture
  React.useEffect(() => {
    if (earthTexture) {
      earthTexture.flipY = true;
    }
  }, [earthTexture]);


  // Remove auto-rotation - globe should only rotate with user interaction

  return (
    <group>
      {/* NASA Earth Base Layer */}
      <mesh
        ref={meshRef}
      >
        <sphereGeometry args={[1, 360, 180]} />
        <meshStandardMaterial 
          map={earthTexture || undefined} 
          transparent
          opacity={1.0}
          color={earthTexture ? "#ffffff" : "#4a5568"}
        />
      </mesh>
      
      {/* Data Overlay Layer */}
      {showDataOverlay && (
        <mesh ref={sstMeshRef}>
          <sphereGeometry args={[1.001, 360, 180]} />
          <meshStandardMaterial
            map={sstTexture || undefined}
            transparent
            opacity={sstTexture ? 0.9 : 0}
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
  selectedDate,
  isTextureLoading = false,
  showSSTOverlay = false, // Legacy support
  onZoomFunctionsReady,
  showMicroplastics = false,
  onMicroplasticsPointHover,
  onMicroplasticsPointClick
}) => {
  const [selectedCoordinates, setSelectedCoordinates] = useState<Coordinates | undefined>(coordinates);
  const { animateToCoordinates, setControls, resetView, zoomIn, zoomOut } = useGlobeCamera();
  
  // Animation controller - handles all animation logic with state machine
  const { requestAnimation, onTextureLoaded } = useAnimationController(animateToCoordinates, {
    debounceMs: 300,
    animationDurationMs: 1200,
    cooldownMs: 100,
    onAnimationStart: (coords) => {
      console.log(`🎬 Animation started to: ${coords.lat.toFixed(4)}°, ${coords.lng.toFixed(4)}°`);
    },
    onAnimationComplete: (coords) => {
      console.log(`🎯 Animation completed to: ${coords.lat.toFixed(4)}°, ${coords.lng.toFixed(4)}°`);
    },
    onStateChange: (state) => {
      console.log(`🎭 Animation state changed to: ${state}`);
    }
  });
  
  // Handle SST texture loaded - notify animation controller
  const handleSstTextureLoaded = useCallback(() => {
    console.log('✅ SST texture loaded');
    onTextureLoaded();
  }, [onTextureLoaded]);
  
  // Track coordinate and date changes
  const prevCoordsRef = useRef(coordinates);
  const prevDateRef = useRef(selectedDate);
  
  // Single effect to handle all coordinate/date changes
  React.useEffect(() => {
    const coordsChanged = coordinates && 
      (!prevCoordsRef.current || 
       Math.abs(coordinates.lat - prevCoordsRef.current.lat) > 0.001 || 
       Math.abs(coordinates.lng - prevCoordsRef.current.lng) > 0.001);
    
    const dateChanged = selectedDate !== prevDateRef.current;
    
    if (coordsChanged || dateChanged) {
      console.log(`📍 Changes detected - Coords: ${coordsChanged}, Date: ${dateChanged}`);
      
      // Update selected coordinates for display
      if (coordinates) {
        setSelectedCoordinates(coordinates);
        
        // Determine animation priority and texture requirements
        const priority = (coordsChanged && dateChanged) ? 'HIGH' : 'NORMAL';
        const requiresTexture = (showDataOverlay || showSSTOverlay) && dateChanged;
        
        // Request animation through the controller
        requestAnimation(coordinates, {
          priority,
          requiresTexture
        });
      }
    }
    
    prevCoordsRef.current = coordinates;
    prevDateRef.current = selectedDate;
  }, [coordinates, selectedDate, showDataOverlay, showSSTOverlay, requestAnimation]);

  // Expose zoom functions to parent component
  React.useEffect(() => {
    if (onZoomFunctionsReady) {
      onZoomFunctionsReady(zoomIn, zoomOut);
    }
  }, [zoomIn, zoomOut, onZoomFunctionsReady]);

  // Animation controller handles its own cleanup

  return (
    <Scene>
      <OrbitControls
        ref={setControls}
        enablePan={false}
        enableZoom={true}
        enableRotate={true}
        minDistance={1.5}
        maxDistance={10}
        rotateSpeed={0.8}
        zoomSpeed={1.0}
        enableDamping={true}
        dampingFactor={0.05}
      />
      
      <GlobeMesh 
        isLoading={isLoading}
        selectedCoordinates={selectedCoordinates}
        showDataOverlay={showDataOverlay || showSSTOverlay} // Support legacy prop
        dataCategory={dataCategory}
        selectedDate={selectedDate}
        showMicroplastics={showMicroplastics}
        onMicroplasticsPointHover={onMicroplasticsPointHover}
        onMicroplasticsPointClick={onMicroplasticsPointClick}
        onSstTextureLoaded={handleSstTextureLoaded}
      />
    </Scene>
  );
};

export default Globe;