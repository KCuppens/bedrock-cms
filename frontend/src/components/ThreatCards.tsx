import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const ThreatCards = () => {
  const threats = [
    {
      type: "Threat",
      title: "Supplier Data Encryption Attack",
      priority: "2",
      priorityColor: "bg-priority-high text-white"
    },
    {
      type: "Vulnerability",
      title: "Vendors Data Encryption Attack",
      priority: "5",
      priorityColor: "bg-foreground text-white"
    },
    {
      type: "Asset",
      title: "Data Center Servers",
      priority: "4",
      priorityColor: "bg-priority-medium text-white"
    }
  ];

  return (
    <div className="space-y-3">
      {threats.map((threat, idx) => (
        <Card key={idx} className="bg-card shadow-subtle border-border/30">
          <CardContent className="p-4">
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground uppercase tracking-wide font-medium">
                {threat.type}
              </div>
              <h3 className="font-medium text-sm leading-tight text-foreground">
                {threat.title}
              </h3>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Priority</span>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${threat.priorityColor}`}>
                  {threat.priority}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default ThreatCards;
