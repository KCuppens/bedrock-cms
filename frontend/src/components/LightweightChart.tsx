import React, { useRef, useEffect, memo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, Calendar } from "lucide-react";

interface ChartData {
  date: string;
  views: number;
  users: number;
}

// Lightweight static data - only what's visible
const getVisibleData = (): ChartData[] => {
  // Only show last 7 days to reduce memory
  return [
    { date: 'Dec 24', views: 4234, users: 3567 },
    { date: 'Dec 25', views: 3123, users: 2654 },
    { date: 'Dec 26', views: 4567, users: 3890 },
    { date: 'Dec 27', views: 5234, users: 4456 },
    { date: 'Dec 28', views: 5890, users: 5123 },
    { date: 'Dec 29', views: 6234, users: 5456 },
    { date: 'Dec 30', views: 5567, users: 4789 },
  ];
};

const LightweightChart = memo(() => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = canvas.offsetWidth;
    canvas.height = 200;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const data = getVisibleData();
    const maxValue = Math.max(...data.flatMap(d => [d.views, d.users]));
    const padding = 40;
    const width = canvas.width - padding * 2;
    const height = canvas.height - padding * 2;

    // Draw simple line chart
    ctx.strokeStyle = 'hsl(var(--primary))';
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((point, index) => {
      const x = padding + (index * width) / (data.length - 1);
      const y = padding + height - (point.views / maxValue) * height;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    // Draw axis labels
    ctx.fillStyle = 'hsl(var(--muted-foreground))';
    ctx.font = '11px sans-serif';

    data.forEach((point, index) => {
      const x = padding + (index * width) / (data.length - 1);
      ctx.fillText(point.date, x - 20, canvas.height - 10);
    });

    // Cleanup
    return () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    };
  }, []);

  const data = getVisibleData();
  const totalViews = data.reduce((sum, d) => sum + d.views, 0);
  const totalUsers = data.reduce((sum, d) => sum + d.users, 0);

  return (
    <Card className="bg-card shadow-card border-border/30">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-primary" />
            <CardTitle className="text-xl font-semibold text-foreground">Weekly Traffic</CardTitle>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              <span>{totalViews.toLocaleString()} views</span>
            </div>
            <div className="text-muted-foreground">
              <span>{totalUsers.toLocaleString()} users</span>
            </div>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          Last 7 days performance
        </p>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[200px] relative">
          <canvas
            ref={canvasRef}
            className="w-full h-full"
            style={{ maxWidth: '100%' }}
          />
        </div>

        <div className="grid grid-cols-2 gap-4 mt-6">
          <div className="p-3 bg-muted/30 rounded-lg text-center">
            <div className="text-xl font-bold text-primary">{totalViews.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">Total Views</div>
          </div>
          <div className="p-3 bg-muted/30 rounded-lg text-center">
            <div className="text-xl font-bold text-secondary">{totalUsers.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">Total Users</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
});

LightweightChart.displayName = 'LightweightChart';

export default LightweightChart;