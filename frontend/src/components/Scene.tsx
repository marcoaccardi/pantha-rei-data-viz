import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { Environment, Stars } from '@react-three/drei';

interface SceneProps {
  children: React.ReactNode;
}

const LoadingFallback: React.FC = () => {
  return (
    <mesh>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial color="#333333" wireframe />
    </mesh>
  );
};

const Scene: React.FC<SceneProps> = ({ children }) => {
  return (
    <Canvas
      camera={{
        position: [0, 0, 5],
        fov: 45,
        near: 0.1,
        far: 1000
      }}
      style={{ background: 'radial-gradient(circle, #001122 0%, #000000 100%)' }}
    >
      <Suspense fallback={<LoadingFallback />}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 5]} intensity={1.2} castShadow />
        <directionalLight position={[-10, -10, -5]} intensity={0.4} />
        <pointLight position={[0, 0, 5]} intensity={0.5} />
        
        <Stars 
          radius={300} 
          depth={60} 
          count={20000} 
          factor={7} 
          saturation={0} 
          fade={true}
        />
        
        <Environment preset="night" />
        
        {children}
      </Suspense>
    </Canvas>
  );
};

export default Scene;