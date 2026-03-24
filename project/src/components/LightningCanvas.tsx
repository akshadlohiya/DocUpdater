import { useEffect, useRef } from 'react';

class Bolt {
  x: number;
  y: number;
  tx: number;
  ty: number;
  life: number;

  constructor(x: number, y: number, targetX: number, targetY: number) {
    this.x = x;
    this.y = y;
    this.tx = targetX;
    this.ty = targetY;
    this.life = 20;
  }

  draw(ctx: CanvasRenderingContext2D) {
    ctx.beginPath();
    ctx.strokeStyle = `rgba(61, 205, 88, ${this.life / 20})`;
    ctx.lineWidth = 2;
    ctx.moveTo(this.x, this.y);

    const cx = this.x + (this.tx - this.x) * 0.5 + (Math.random() - 0.5) * 100;
    const cy = this.y + (this.ty - this.y) * 0.5 + (Math.random() - 0.5) * 100;

    ctx.quadraticCurveTo(cx, cy, this.tx, this.ty);
    ctx.stroke();
    this.life--;
  }
}

export default function LightningCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = window.innerWidth;
    let height = window.innerHeight;
    const lastMouse = { x: width / 2, y: height / 2 };
    const bolts: Bolt[] = [];

    canvas.width = width;
    canvas.height = height;

    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    const handleMouseMove = (e: MouseEvent) => {
      lastMouse.x = e.clientX;
      lastMouse.y = e.clientY;
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);

    let animationFrameId: number;

    const animate = () => {
      ctx.fillStyle = 'rgba(5, 10, 14, 0.2)';
      ctx.fillRect(0, 0, width, height);

      if (Math.random() > 0.85) {
        bolts.push(
          new Bolt(
            Math.random() * width,
            Math.random() * height,
            lastMouse.x,
            lastMouse.y
          )
        );
      }

      for (let i = bolts.length - 1; i >= 0; i--) {
        if (bolts[i].life <= 0) {
          bolts.splice(i, 1);
        } else {
          bolts[i].draw(ctx);
        }
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed top-0 left-0 z-0 pointer-events-none"
    />
  );
}
