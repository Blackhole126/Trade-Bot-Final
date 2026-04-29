import { useEffect, useState, useRef } from 'react';

interface Star {
  x: number;
  y: number;
  z: number;
  size: number;
  speed: number;
  twinkle: number;
  twinkleSpeed: number;
}

interface Nebula {
  x: number;
  y: number;
  radius: number;
  color: string;
  opacity: number;
  pulse: number;
  pulseSpeed: number;
}

const UniGuruBackground = () => {
  const [mounted, setMounted] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | undefined>(undefined);
  const starsRef = useRef<Star[]>([]);
  const nebulasRef = useRef<Nebula[]>([]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Create stars - 3D space effect
    const starCount = 500;
    const stars: Star[] = [];
    for (let i = 0; i < starCount; i++) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        z: Math.random() * 2000, // Depth
        size: Math.random() * 2 + 0.5,
        speed: Math.random() * 0.5 + 0.1,
        twinkle: Math.random() * Math.PI * 2,
        twinkleSpeed: Math.random() * 0.02 + 0.01,
      });
    }
    starsRef.current = stars;

    // Create nebulas (colorful space clouds)
    const nebulaCount = 3;
    const nebulas: Nebula[] = [];
    const nebulaColors = [
      'rgba(147, 51, 234, 0.15)',   // Purple
      'rgba(37, 99, 235, 0.12)',    // Blue
      'rgba(168, 85, 247, 0.1)',    // Light Purple
      'rgba(59, 130, 246, 0.1)',    // Light Blue
    ];
    
    for (let i = 0; i < nebulaCount; i++) {
      nebulas.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        radius: Math.random() * 400 + 200,
        color: nebulaColors[Math.floor(Math.random() * nebulaColors.length)],
        opacity: Math.random() * 0.3 + 0.1,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: Math.random() * 0.005 + 0.002,
      });
    }
    nebulasRef.current = nebulas;

    // Animation loop
    const animate = () => {
      // Clear with deep space black background
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw nebulas first (behind stars)
      nebulas.forEach((nebula) => {
        nebula.pulse += nebula.pulseSpeed;
        const currentOpacity = nebula.opacity + Math.sin(nebula.pulse) * 0.1;
        
        // Create radial gradient for nebula
        const gradient = ctx.createRadialGradient(
          nebula.x, nebula.y, 0,
          nebula.x, nebula.y, nebula.radius
        );
        
        const colorParts = nebula.color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (colorParts) {
          const r = parseInt(colorParts[1]);
          const g = parseInt(colorParts[2]);
          const b = parseInt(colorParts[3]);
          gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${currentOpacity})`);
          gradient.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${currentOpacity * 0.5})`);
          gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
        }
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(nebula.x, nebula.y, nebula.radius, 0, Math.PI * 2);
        ctx.fill();
      });

      // Draw stars with 3D depth effect
      stars.forEach((star) => {
        // Update star position (moving towards camera)
        star.z -= star.speed;
        star.twinkle += star.twinkleSpeed;

        // Reset star if it's too close
        if (star.z <= 0) {
          star.z = 2000;
          star.x = Math.random() * canvas.width;
          star.y = Math.random() * canvas.height;
        }

        // Calculate 2D position from 3D
        const x = (star.x - canvas.width / 2) * (1000 / star.z) + canvas.width / 2;
        const y = (star.y - canvas.height / 2) * (1000 / star.z) + canvas.height / 2;
        
        // Calculate size based on depth
        const size = (star.size * 1000) / star.z;
        
        // Twinkle effect
        const twinkle = (Math.sin(star.twinkle) + 1) / 2;
        const opacity = 0.5 + twinkle * 0.5;

        // Draw star with glow
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        
        // Create glow gradient
        const glowGradient = ctx.createRadialGradient(x, y, 0, x, y, size * 3);
        glowGradient.addColorStop(0, `rgba(255, 255, 255, ${opacity})`);
        glowGradient.addColorStop(0.3, `rgba(255, 255, 255, ${opacity * 0.5})`);
        glowGradient.addColorStop(0.6, `rgba(147, 51, 234, ${opacity * 0.3})`);
        glowGradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
        
        ctx.fillStyle = glowGradient;
        ctx.fill();

        // Draw bright center
        ctx.beginPath();
        ctx.arc(x, y, size * 0.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${opacity})`;
        ctx.fill();
      });

      // Draw star trails (motion blur effect)
      stars.forEach((star) => {
        if (star.z < 500) { // Only draw trails for close stars
          const x = (star.x - canvas.width / 2) * (1000 / star.z) + canvas.width / 2;
          const y = (star.y - canvas.height / 2) * (1000 / star.z) + canvas.height / 2;
          const prevX = (star.x - canvas.width / 2) * (1000 / (star.z + star.speed * 10)) + canvas.width / 2;
          const prevY = (star.y - canvas.height / 2) * (1000 / (star.z + star.speed * 10)) + canvas.height / 2;
          
          ctx.beginPath();
          ctx.moveTo(prevX, prevY);
          ctx.lineTo(x, y);
          ctx.strokeStyle = `rgba(255, 255, 255, ${0.3 * (500 - star.z) / 500})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      });

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [mounted]);

  if (!mounted) return null;

  return (
    <div 
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
      style={{ 
        backgroundColor: '#000000',
      }}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ 
          backgroundColor: '#000000',
        }}
      />
    </div>
  );
};

export default UniGuruBackground;
