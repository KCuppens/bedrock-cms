import { memo, useMemo, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, Calendar } from "lucide-react";

const trafficData = [
  { date: 'Dec 1', views: 2340, users: 1890 },
  { date: 'Dec 2', views: 2890, users: 2120 },
  { date: 'Dec 3', views: 2156, users: 1654 },
  { date: 'Dec 4', views: 3421, users: 2890 },
  { date: 'Dec 5', views: 2987, users: 2345 },
  { date: 'Dec 6', views: 4123, users: 3421 },
  { date: 'Dec 7', views: 3789, users: 3123 },
  { date: 'Dec 8', views: 2456, users: 1987 },
  { date: 'Dec 9', views: 3654, users: 2987 },
  { date: 'Dec 10', views: 4567, users: 3890 },
  { date: 'Dec 11', views: 3234, users: 2654 },
  { date: 'Dec 12', views: 4890, users: 4123 },
  { date: 'Dec 13', views: 3567, users: 2890 },
  { date: 'Dec 14', views: 4234, users: 3567 },
  { date: 'Dec 15', views: 5123, users: 4234 },
  { date: 'Dec 16', views: 3890, users: 3123 },
  { date: 'Dec 17', views: 4567, users: 3890 },
  { date: 'Dec 18', views: 5234, users: 4456 },
  { date: 'Dec 19', views: 4890, users: 4123 },
  { date: 'Dec 20', views: 5567, users: 4789 },
  { date: 'Dec 21', views: 6123, users: 5234 },
  { date: 'Dec 22', views: 5890, users: 4987 },
  { date: 'Dec 23', views: 6456, users: 5567 },
  { date: 'Dec 24', views: 4234, users: 3567 },
  { date: 'Dec 25', views: 3123, users: 2654 },
  { date: 'Dec 26', views: 4567, users: 3890 },
  { date: 'Dec 27', views: 5234, users: 4456 },
  { date: 'Dec 28', views: 5890, users: 5123 },
  { date: 'Dec 29', views: 6234, users: 5456 },
  { date: 'Dec 30', views: 5567, users: 4789 },
];

const CustomTooltip = memo(({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
        <p className="font-medium text-foreground">{label}</p>
        <div className="space-y-1">
          <p className="text-primary">
            Views: <span className="font-semibold">{payload[0].value.toLocaleString()}</span>
          </p>
          {payload[1] && (
            <p className="text-secondary">
              Users: <span className="font-semibold">{payload[1].value.toLocaleString()}</span>
            </p>
          )}
        </div>
      </div>
    );
  }
  return null;
});

CustomTooltip.displayName = 'CustomTooltip';

const TrafficViewsChart = memo(() => {
  const statistics = useMemo(() => {
    const totalViews = trafficData.reduce((sum, day) => sum + day.views, 0);
    const totalUsers = trafficData.reduce((sum, day) => sum + day.users, 0);
    const avgViews = Math.round(totalViews / trafficData.length);
    const avgUsers = Math.round(totalUsers / trafficData.length);

    return {
      totalViews,
      totalUsers,
      avgViews,
      avgUsers,
    };
  }, []);

  const tickFormatter = useCallback((value: number) => `${(value / 1000).toFixed(0)}k`, []);

  return (
    <Card className="bg-card shadow-card border-border/30">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-primary" />
            <CardTitle className="text-xl font-semibold text-foreground">Daily Traffic Views</CardTitle>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              <span>{statistics.totalViews.toLocaleString()} views</span>
            </div>
            <div className="text-muted-foreground">
              <span>{statistics.totalUsers.toLocaleString()} users</span>
            </div>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          Daily website traffic for the last 30 days
        </p>
      </CardHeader>
      <CardContent>
        <div className="h-80 w-full mb-6">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trafficData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <defs>
                <linearGradient id="viewsGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.05}/>
                </linearGradient>
                <linearGradient id="usersGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--secondary))" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(var(--secondary))" stopOpacity={0.05}/>
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                tickFormatter={tickFormatter}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="users"
                stroke="hsl(var(--secondary))"
                strokeWidth={2}
                fill="url(#usersGradient)"
              />
              <Area
                type="monotone"
                dataKey="views"
                stroke="hsl(var(--primary))"
                strokeWidth={3}
                fill="url(#viewsGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Stats Summary */}
        <div className="space-y-3">
          <h4 className="font-medium text-foreground mb-3">Summary Statistics</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-muted/30 rounded-lg text-center">
              <div className="text-2xl font-bold text-primary">{statistics.totalViews.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">Total Views</div>
            </div>
            <div className="p-4 bg-muted/30 rounded-lg text-center">
              <div className="text-2xl font-bold text-secondary">{statistics.totalUsers.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">Total Users</div>
            </div>
            <div className="p-4 bg-muted/30 rounded-lg text-center">
              <div className="text-2xl font-bold text-foreground">{statistics.avgViews.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">Avg Daily Views</div>
            </div>
            <div className="p-4 bg-muted/30 rounded-lg text-center">
              <div className="text-2xl font-bold text-foreground">{statistics.avgUsers.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">Avg Daily Users</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
});

TrafficViewsChart.displayName = 'TrafficViewsChart';

export default TrafficViewsChart;
