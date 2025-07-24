import { useRef, useCallback } from 'react';
import { Vector3 } from 'three';
import type { Coordinates } from '../utils/types';
import { latLngToVector3 } from '../utils/coordinates';

export function useGlobeCamera() {
  const currentTargetRef = useRef<Coordinates | null>(null);
  const orbitControlsRef = useRef<any>(null);

  const animateToCoordinates = useCallback((coords: Coordinates) => {
    try {
      // Prevent duplicate animations to the same coordinates
      if (currentTargetRef.current && 
          Math.abs(currentTargetRef.current.lat - coords.lat) < 0.001 && 
          Math.abs(currentTargetRef.current.lng - coords.lng) < 0.001) {
        console.log('Skipping duplicate animation to same coordinates');
        return;
      }

      currentTargetRef.current = coords;

      if (orbitControlsRef.current && orbitControlsRef.current.object) {
        const camera = orbitControlsRef.current.object;
        const controls = orbitControlsRef.current;
        
        // Calculate the 3D position of the selected coordinates on the globe
        const targetPosition = latLngToVector3(coords.lat, coords.lng, 1);
        
        // Calculate the ideal camera position to look at this point
        // We want the camera to be positioned so the target point is centered
        const idealCameraPosition = targetPosition.clone().multiplyScalar(2.5); // Distance from globe
        
        // Get current camera position and target position for animation
        const startCameraPosition = camera.position.clone();
        const startTime = Date.now();
        const duration = 1200; // Longer for smooth rotation + zoom
        
        const animateCamera = () => {
          try {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeInOut = (t: number) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
            const easedProgress = easeInOut(progress);
            
            // Interpolate camera position
            const currentCameraPosition = startCameraPosition.clone().lerp(idealCameraPosition, easedProgress);
            camera.position.copy(currentCameraPosition);
            
            // Always look at the center of the globe
            camera.lookAt(0, 0, 0);
            
            // Update controls
            if (controls && controls.update) {
              controls.update();
            }
            
            if (progress < 1) {
              requestAnimationFrame(animateCamera);
            }
          } catch (error) {
            console.warn('Animation error:', error);
          }
        };
        
        animateCamera();
      }

      console.log(`Centering on coordinates: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}`);
    } catch (error) {
      console.error('Error in animateToCoordinates:', error);
    }
  }, []);

  const zoomIn = useCallback(() => {
    if (orbitControlsRef.current && orbitControlsRef.current.object) {
      const camera = orbitControlsRef.current.object;
      const controls = orbitControlsRef.current;
      
      const currentDistance = camera.position.length();
      const targetDistance = Math.max(currentDistance * 0.7, 1.5); // Zoom in, but not too close
      
      const startTime = Date.now();
      const duration = 500;
      
      const animateZoom = () => {
        try {
          const elapsed = Date.now() - startTime;
          const progress = Math.min(elapsed / duration, 1);
          
          const easeInOut = (t: number) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
          const easedProgress = easeInOut(progress);
          
          const newDistance = currentDistance + (targetDistance - currentDistance) * easedProgress;
          const direction = camera.position.clone().normalize();
          camera.position.copy(direction.multiplyScalar(newDistance));
          
          if (controls && controls.update) {
            controls.update();
          }
          
          if (progress < 1) {
            requestAnimationFrame(animateZoom);
          }
        } catch (error) {
          console.warn('Zoom animation error:', error);
        }
      };
      
      animateZoom();
    }
  }, []);

  const zoomOut = useCallback(() => {
    if (orbitControlsRef.current && orbitControlsRef.current.object) {
      const camera = orbitControlsRef.current.object;
      const controls = orbitControlsRef.current;
      
      const currentDistance = camera.position.length();
      const targetDistance = Math.min(currentDistance * 1.4, 10); // Zoom out, but not too far
      
      const startTime = Date.now();
      const duration = 500;
      
      const animateZoom = () => {
        try {
          const elapsed = Date.now() - startTime;
          const progress = Math.min(elapsed / duration, 1);
          
          const easeInOut = (t: number) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
          const easedProgress = easeInOut(progress);
          
          const newDistance = currentDistance + (targetDistance - currentDistance) * easedProgress;
          const direction = camera.position.clone().normalize();
          camera.position.copy(direction.multiplyScalar(newDistance));
          
          if (controls && controls.update) {
            controls.update();
          }
          
          if (progress < 1) {
            requestAnimationFrame(animateZoom);
          }
        } catch (error) {
          console.warn('Zoom animation error:', error);
        }
      };
      
      animateZoom();
    }
  }, []);

  const getCurrentView = useCallback(() => {
    return {
      position: [0, 0, 5] as [number, number, number],
      target: [0, 0, 0] as [number, number, number],
      zoom: 5
    };
  }, []);

  const resetView = useCallback(() => {
    currentTargetRef.current = null;
    if (orbitControlsRef.current && orbitControlsRef.current.object) {
      const camera = orbitControlsRef.current.object;
      const controls = orbitControlsRef.current;
      
      // Reset to default distance
      const direction = camera.position.clone().normalize();
      camera.position.copy(direction.multiplyScalar(5));
      controls.update();
    }
    console.log('Reset view to default position');
  }, []);

  return {
    animateToCoordinates,
    getCurrentView,
    resetView,
    zoomIn,
    zoomOut,
    orbitControlsRef
  };
}