import { useRef, useCallback } from 'react';
import { Vector3 } from 'three';
import * as THREE from 'three';
import type { Coordinates } from '../utils/types';
import { latLngToVector3 } from '../utils/coordinates';

export function useGlobeCamera() {
  const currentTargetRef = useRef<Coordinates | null>(null);
  const orbitControlsRef = useRef<any>(null);
  const animationFrameRef = useRef<number | null>(null);

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

      // Function to execute animation when controls are ready
      const executeAnimation = () => {
        if (!orbitControlsRef.current || !orbitControlsRef.current.object) {
          // If controls not ready, try again in a moment
          setTimeout(executeAnimation, 100);
          return;
        }
        const controls = orbitControlsRef.current;
        const camera = controls.object;
        
        // Ensure camera has a valid initial position
        if (camera.position.length() < 0.1) {
          // If camera is too close to origin, set it to a default position
          camera.position.set(0, 0, 5);
          controls.update();
        }
        
        // Calculate the 3D position of the selected coordinates on the globe
        const targetPosition = latLngToVector3(coords.lat, coords.lng, 1);
        
        // Calculate the ideal camera position to look at this point
        // Camera should be positioned so the target point is centered
        const idealCameraPosition = targetPosition.clone().multiplyScalar(2.5); // Distance from globe
        
        // Get current camera position for smooth animation
        const startCameraPosition = camera.position.clone();
        const startTime = Date.now();
        const duration = 1200; // Smooth rotation duration
        
        const animateCamera = () => {
          try {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeInOut = (t: number) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
            const easedProgress = easeInOut(progress);
            
            // Use spherical interpolation for natural globe rotation
            // This prevents the camera from taking weird paths through the globe
            const startDirection = startCameraPosition.clone().normalize();
            const idealDirection = idealCameraPosition.clone().normalize();
            
            // Calculate the angle between start and target directions
            const angle = startDirection.angleTo(idealDirection);
            
            // If angle is very small, use linear interpolation to avoid numerical issues
            let currentDirection;
            if (angle < 0.001) {
              currentDirection = startDirection.clone().lerp(idealDirection, easedProgress);
            } else {
              // Use spherical interpolation (slerp) for smooth rotation along the sphere
              // Create a quaternion that rotates from start to ideal direction
              const axis = new Vector3().crossVectors(startDirection, idealDirection).normalize();
              const quaternion = new THREE.Quaternion().setFromAxisAngle(axis, angle * easedProgress);
              currentDirection = startDirection.clone().applyQuaternion(quaternion);
            }
            
            // Maintain consistent distance from globe center
            const startDistance = startCameraPosition.length();
            const idealDistance = idealCameraPosition.length();
            const currentDistance = startDistance + (idealDistance - startDistance) * easedProgress;
            
            const currentCameraPosition = currentDirection.multiplyScalar(currentDistance);
            camera.position.copy(currentCameraPosition);
            
            // Always look at the center of the globe
            camera.lookAt(0, 0, 0);
            controls.target.set(0, 0, 0);
            
            // Update controls
            if (controls && controls.update) {
              controls.update();
            }
            
            if (progress < 1) {
              animationFrameRef.current = requestAnimationFrame(animateCamera);
            } else {
              animationFrameRef.current = null;
            }
          } catch (error) {
            console.error('Camera animation error:', error);
            animationFrameRef.current = null;
          }
        };
        
        animateCamera();
      };

      // Start the animation execution
      executeAnimation();

    } catch (error) {
      console.error('Animation error:', error);
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
          console.error('Zoom error:', error);
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
          console.error('Zoom error:', error);
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