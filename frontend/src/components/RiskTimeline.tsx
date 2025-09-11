import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const data = [
  { name: 'Mon', value: 20 },
  { name: 'Tue', value: 35 },
  { name: 'Wed', value: 25 },
  { name: 'Thu', value: 15 },
  { name: 'Fri', value: 45 },
  { name: 'Sat', value: 65 },
  { name: 'Sun', value: 85 },
];

const RiskTimeline = () => {
  return (
    <Card className="bg-card shadow-card border-border/30">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-foreground">Risk Timeline</CardTitle>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="sm" className="text-xs h-8 px-3">12 Months</Button>
            <Button size="sm" className="text-xs h-8 px-3 bg-foreground text-white hover:bg-foreground/90">30 Days</Button>
            <Button variant="outline" size="sm" className="text-xs h-8 px-3">1 Week</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <XAxis 
                dataKey="name" 
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis hide />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="hsl(var(--primary))" 
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 4, fill: "hsl(var(--primary))" }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="hsl(var(--primary) / 0.4)"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

export default RiskTimeline;