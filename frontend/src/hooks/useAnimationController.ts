import { useRef, useCallback, useState, useEffect } from 'react';
import type { Coordinates } from '../utils/types';

type AnimationState = 
  | 'IDLE'           // Ready to accept new animation requests
  | 'DEBOUNCING'     // Ignoring rapid requests within debounce window  
  | 'QUEUED'         // Animation request queued, about to start
  | 'WAITING_TEXTURE'// Waiting for texture to load before animating
  | 'ANIMATING'      // Currently executing camera animation
  | 'COOLDOWN';      // Brief pause after animation completes

interface AnimationRequest {
  id: string;
  coordinates: Coordinates;
  priority: 'HIGH' | 'NORMAL'; // HIGH = date+location change, NORMAL = location only
  requiresTexture: boolean;
  timestamp: number;
}

interface UseAnimationControllerOptions {
  debounceMs?: number;
  animationDurationMs?: number; 
  cooldownMs?: number;
  onAnimationStart?: (coords: Coordinates) => void;
  onAnimationComplete?: (coords: Coordinates) => void;
  onStateChange?: (state: AnimationState) => void;
}

export function useAnimationController(
  animateToCoordinates: (coords: Coordinates) => void,
  options: UseAnimationControllerOptions = {}
) {
  const {
    debounceMs = 300,
    animationDurationMs = 1200,
    cooldownMs = 100,
    onAnimationStart,
    onAnimationComplete,
    onStateChange
  } = options;

  // State machine
  const [state, setState] = useState<AnimationState>('IDLE');
  const stateRef = useRef<AnimationState>('IDLE');
  
  // Animation queue and tracking
  const currentRequestRef = useRef<AnimationRequest | null>(null);
  const queuedRequestRef = useRef<AnimationRequest | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const requestIdCounterRef = useRef(0);
  
  // Texture loading tracking
  const isWaitingForTextureRef = useRef(false);
  const textureLoadedCallbackRef = useRef<(() => void) | null>(null);

  // Internal state setter that keeps ref in sync
  const setAnimationState = useCallback((newState: AnimationState) => {
    console.log(`🎭 Animation State: ${stateRef.current} → ${newState}`);
    stateRef.current = newState;
    setState(newState);
    onStateChange?.(newState);
  }, [onStateChange]);

  // Clear any active timeout
  const clearAnimationTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Execute the actual camera animation
  const executeAnimation = useCallback((request: AnimationRequest) => {
    console.log(`🚀 Executing animation to: ${request.coordinates.lat.toFixed(4)}°, ${request.coordinates.lng.toFixed(4)}°`);
    
    setAnimationState('ANIMATING');
    onAnimationStart?.(request.coordinates);
    
    // Execute the camera animation
    animateToCoordinates(request.coordinates);
    
    // Set timeout to complete animation
    timeoutRef.current = setTimeout(() => {
      console.log(`✅ Animation completed for: ${request.coordinates.lat.toFixed(4)}°, ${request.coordinates.lng.toFixed(4)}°`);
      
      onAnimationComplete?.(request.coordinates);
      currentRequestRef.current = null;
      
      // Brief cooldown to prevent visual jarring
      if (cooldownMs > 0) {
        setAnimationState('COOLDOWN');
        timeoutRef.current = setTimeout(() => {
          setAnimationState('IDLE');
          processQueue(); // Check if there are queued requests
        }, cooldownMs);
      } else {
        setAnimationState('IDLE'); 
        processQueue();
      }
    }, animationDurationMs);
    
  }, [animateToCoordinates, animationDurationMs, cooldownMs, onAnimationStart, onAnimationComplete, setAnimationState]);

  // Process the animation queue
  const processQueue = useCallback(() => {
    if (stateRef.current !== 'IDLE') return;
    
    const nextRequest = queuedRequestRef.current;
    if (!nextRequest) return;
    
    console.log(`📋 Processing queued request: ${nextRequest.id}`);
    queuedRequestRef.current = null;
    currentRequestRef.current = nextRequest;
    
    // Check if we need to wait for texture
    if (nextRequest.requiresTexture && !isWaitingForTextureRef.current) {
      console.log(`⏳ Waiting for texture before animation: ${nextRequest.id}`);
      setAnimationState('WAITING_TEXTURE');
      isWaitingForTextureRef.current = true;
      
      // Store callback for when texture loads
      textureLoadedCallbackRef.current = () => {
        if (stateRef.current === 'WAITING_TEXTURE' && currentRequestRef.current?.id === nextRequest.id) {
          executeAnimation(nextRequest);
        }
      };
    } else {
      // Execute immediately
      setAnimationState('QUEUED');
      timeoutRef.current = setTimeout(() => {
        executeAnimation(nextRequest);
      }, 50); // Small delay for smooth transition
    }
  }, [executeAnimation, setAnimationState]);

  // Main animation request handler
  const requestAnimation = useCallback((
    coordinates: Coordinates,
    options: {
      priority?: 'HIGH' | 'NORMAL';
      requiresTexture?: boolean;
      force?: boolean; // Skip debouncing
    } = {}
  ) => {
    const { priority = 'NORMAL', requiresTexture = false, force = false } = options;
    
    // Generate unique request ID
    const requestId = `anim_${++requestIdCounterRef.current}`;
    const timestamp = Date.now();
    
    const newRequest: AnimationRequest = {
      id: requestId,
      coordinates,
      priority,
      requiresTexture,
      timestamp
    };
    
    console.log(`📥 Animation request: ${requestId} (${priority}) to ${coordinates.lat.toFixed(4)}°, ${coordinates.lng.toFixed(4)}°`);

    // Check for duplicate coordinates
    if (currentRequestRef.current) {
      const current = currentRequestRef.current;
      const latDiff = Math.abs(current.coordinates.lat - coordinates.lat);
      const lngDiff = Math.abs(current.coordinates.lng - coordinates.lng);
      if (latDiff < 0.001 && lngDiff < 0.001) {
        console.log(`🔄 Ignoring duplicate animation request to same coordinates`);
        return;
      }
    }

    // Handle different states
    switch (stateRef.current) {
      case 'IDLE':
        // Start new animation immediately by queuing it and processing
        queuedRequestRef.current = newRequest;
        processQueue();
        break;
        
      case 'DEBOUNCING':
        if (force || priority === 'HIGH') {
          // High priority or forced requests override debouncing
          clearAnimationTimeout();
          queuedRequestRef.current = newRequest;
          setAnimationState('IDLE');
          processQueue();
        } else {
          // Update queued request but stay in debouncing
          queuedRequestRef.current = newRequest;
        }
        break;
        
      case 'QUEUED':
      case 'WAITING_TEXTURE':
        // Replace queued/waiting request
        if (priority === 'HIGH' || !queuedRequestRef.current || priority >= queuedRequestRef.current.priority) {
          queuedRequestRef.current = newRequest;
          console.log(`🔄 Replaced queued animation with: ${requestId}`);
        }
        break;
        
      case 'ANIMATING':
        // Queue new request to execute after current animation
        if (priority === 'HIGH' || !queuedRequestRef.current || priority >= queuedRequestRef.current.priority) {
          queuedRequestRef.current = newRequest;
          console.log(`📋 Queued animation for after current: ${requestId}`);
        }
        break;
        
      case 'COOLDOWN':
        // Replace any queued request and it will execute after cooldown
        queuedRequestRef.current = newRequest;
        break;
        
      default:
        console.warn(`🚨 Unknown animation state: ${stateRef.current}`);
        break;
    }
  }, [clearTimeout, processQueue, setAnimationState]);

  // Handle texture loaded event
  const onTextureLoaded = useCallback(() => {
    console.log(`🖼️ Texture loaded - checking for waiting animations`);
    isWaitingForTextureRef.current = false;
    
    if (textureLoadedCallbackRef.current) {
      const callback = textureLoadedCallbackRef.current;
      textureLoadedCallbackRef.current = null;
      callback();
    }
  }, []);

  // Reset animation system (for error recovery)
  const reset = useCallback(() => {
    console.log(`🔄 Resetting animation controller`);
    clearAnimationTimeout();
    currentRequestRef.current = null;
    queuedRequestRef.current = null;
    isWaitingForTextureRef.current = false;
    textureLoadedCallbackRef.current = null;
    setAnimationState('IDLE');
  }, [clearTimeout, setAnimationState]);

  // Get current animation status  
  const getStatus = useCallback(() => {
    return {
      state: stateRef.current,
      currentRequest: currentRequestRef.current,
      queuedRequest: queuedRequestRef.current,
      isWaitingForTexture: isWaitingForTextureRef.current
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearAnimationTimeout();
    };
  }, [clearAnimationTimeout]);

  return {
    // Main interface
    requestAnimation,
    onTextureLoaded,
    
    // Status and control
    state,
    getStatus,
    reset,
    
    // For debugging
    isIdle: state === 'IDLE',
    isAnimating: state === 'ANIMATING' || state === 'WAITING_TEXTURE',
    hasQueuedRequest: queuedRequestRef.current !== null
  };
}