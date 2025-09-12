import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MoreHorizontal } from "lucide-react";

const AssessmentsTable = () => {
  const assessments = [
    {
      id: "RA-1817",
      assessor: {
        name: "Alex Johnson",
        avatar: "/placeholder.svg",
        initials: "AJ"
      },
      state: "Treatment",
      stateColor: "bg-status-treatment text-status-treatment-text",
      dueDate: "Nov 23, 2025",
      status: "In progress",
      statusColor: "text-status-in-progress",
      statusDot: "bg-status-in-progress",
      initiative: "Third Risk Audit"
    },
    {
      id: "LP-1459",
      assessor: {
        name: "Casey Brown",
        avatar: "/placeholder.svg",
        initials: "CB"
      },
      state: "Transfer",
      stateColor: "bg-status-transfer text-status-transfer-text",
      dueDate: "Oct 18, 2025",
      status: "In progress",
      statusColor: "text-status-in-progress",
      statusDot: "bg-status-in-progress",
      initiative: "Cloud Review"
    },
    {
      id: "BV-1278",
      assessor: {
        name: "Anna Lee",
        avatar: "/placeholder.svg",
        initials: "AL"
      },
      state: "Monitoring",
      stateColor: "bg-status-monitoring text-status-monitoring-text",
      dueDate: "Sep 14, 2024",
      status: "Completed",
      statusColor: "text-status-completed",
      statusDot: "bg-status-completed",
      initiative: "Security Program"
    }
  ];

  return (
    <Card className="bg-card shadow-card border-border/30">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-foreground">Assessments</CardTitle>
          <div className="flex items-center gap-2">
            <Button size="sm" className="bg-foreground text-white hover:bg-foreground/90 h-8">
              Map Assessment
            </Button>
            <Button variant="outline" size="sm" className="h-8">
              New Assessment
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">#</th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Assessor</th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">State</th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Due Date</th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Status</th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Linked Initiatives</th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground"></th>
              </tr>
            </thead>
            <tbody>
              {assessments.map((assessment) => (
                <tr key={assessment.id} className="border-b border-border/20 last:border-0">
                  <td className="py-4 px-2 text-sm text-muted-foreground">
                    {assessment.id}
                  </td>
                  <td className="py-4 px-2">
                    <div className="flex items-center gap-3">
                      <Avatar className="w-8 h-8">
                        <AvatarImage src={assessment.assessor.avatar} />
                        <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                          {assessment.assessor.initials}
                        </AvatarFallback>
                      </Avatar>
                      <span className="text-sm font-medium text-foreground">{assessment.assessor.name}</span>
                    </div>
                  </td>
                  <td className="py-4 px-2">
                    <Badge variant="secondary" className={`${assessment.stateColor} border-0 font-medium`}>
                      {assessment.state}
                    </Badge>
                  </td>
                  <td className="py-4 px-2 text-sm text-foreground">{assessment.dueDate}</td>
                  <td className="py-4 px-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${assessment.statusDot}`} />
                      <span className={`text-sm font-medium ${assessment.statusColor}`}>
                        {assessment.status}
                      </span>
                    </div>
                  </td>
                  <td className="py-4 px-2 text-sm text-foreground">{assessment.initiative}</td>
                  <td className="py-4 px-2">
                    <Button variant="ghost" size="sm">
                      <MoreHorizontal className="w-4 h-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
};

export default AssessmentsTable;