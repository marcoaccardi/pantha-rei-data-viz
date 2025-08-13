import { useRef, useCallback, useState } from 'react';
import { Vector3 } from 'three';
import type { Coordinates } from '../utils/types';
import { latLngToVector3 } from '../utils/coordinates';

export function useGlobeCamera() {
  const currentTargetRef = useRef<Coordinates | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const [controls, setControls] = useState<any>(null); // State to hold OrbitControls instance

  const animateToCoordinates = useCallback((coords: Coordinates) => {
    try {
      // Cancel any ongoing animation
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }

      // Prevent duplicate animations to the same coordinates
      if (currentTargetRef.current && 
          Math.abs(currentTargetRef.current.lat - coords.lat) < 0.001 && 
          Math.abs(currentTargetRef.current.lng - coords.lng) < 0.001) {
        return;
      }

      currentTargetRef.current = coords;

      if (controls && controls.object) { // Use the controls state variable
        controls.enabled = false; // Disable controls during animation
        const camera = controls.object;
        
        // Calculate the 3D position of the selected coordinates on the globe
        const targetPosition = latLngToVector3(coords.lat, coords.lng, 1); // Point on globe
        
        // Calculate the ideal camera position relative to the target
        // This vector points from the globe's center to the target, then scaled outwards
        const idealCameraPosition = targetPosition.clone().multiplyScalar(2.5); // Distance from globe
        
        // Get current camera position and target for animation
        const startCameraPosition = camera.position.clone();
        const startTargetPosition = controls.target.clone();
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
            
            // Interpolate controls target
            const currentTarget = startTargetPosition.clone().lerp(targetPosition, easedProgress);
            controls.target.copy(currentTarget);
            
            // Update controls
            if (controls && controls.update) {
              controls.update();
            }
            
            if (progress < 1) {
              animationFrameRef.current = requestAnimationFrame(animateCamera);
            } else {
              animationFrameRef.current = null;
              controls.enabled = true; // Re-enable controls after animation
            }
          } catch (error) {
            animationFrameRef.current = null;
            controls.enabled = true; // Re-enable controls on error
          }
        };
        
        animateCamera();
      }

    } catch (error) {
    }
  }, [controls]); // Add controls to dependency array

  const zoomIn = useCallback(() => {
    if (controls && controls.object) { // Use the controls state variable
      const camera = controls.object;
      
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
        }
      };
      
      animateZoom();
    }
  }, [controls]); // Add controls to dependency array

  const zoomOut = useCallback(() => {
    if (controls && controls.object) { // Use the controls state variable
      const camera = controls.object;
      
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
        }
      };
      
      animateZoom();
    }
  }, [controls]); // Add controls to dependency array

  const getCurrentView = useCallback(() => {
    return {
      position: [0, 0, 5] as [number, number, number],
      target: [0, 0, 0] as [number, number, number],
      zoom: 5
    };
  }, []);

  const resetView = useCallback(() => {
    currentTargetRef.current = null;
    if (controls && controls.object) { // Use the controls state variable
      const camera = controls.object;
      
      // Reset to default distance
      const direction = camera.position.clone().normalize();
      camera.position.copy(direction.multiplyScalar(5));
      controls.update();
    }
  }, [controls]); // Add controls to dependency array

  return {
    animateToCoordinates,
    getCurrentView,
    resetView,
    zoomIn,
    zoomOut,
    setControls // Return setControls
  };
}