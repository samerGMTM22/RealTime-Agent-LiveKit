import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Clock, MessageCircle, Calendar } from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";

interface SessionHistoryProps {
  agentConfigId: number;
}

interface SessionSummary {
  sessionId: string;
  startTime: Date;
  endTime: Date;
  messageCount: number;
  duration: number;
  agentConfigId: number;
}

export default function SessionHistory({ agentConfigId }: SessionHistoryProps) {
  const { data: sessions = [], isLoading } = useQuery<SessionSummary[]>({
    queryKey: ["/api/sessions/history", agentConfigId],
    enabled: !!agentConfigId,
  });

  if (isLoading) {
    return (
      <Card className="glass-card rounded-2xl premium-shadow">
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-electric-blue"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass-card rounded-2xl premium-shadow">
      <CardHeader>
        <CardTitle className="flex items-center text-xl font-semibold">
          <Clock className="text-cyber-cyan mr-3" />
          Session History
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96 pr-4">
          {sessions.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              <Clock className="mx-auto h-12 w-12 text-gray-600 mb-4" />
              <p>No sessions yet</p>
              <p className="text-sm">Start a voice session to see session history here</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.map((session: SessionSummary) => (
                <div key={session.sessionId} className="glass-card p-4 rounded-lg border border-gray-700/30 hover:border-cyber-cyan/50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <Calendar className="h-4 w-4 text-cyber-cyan" />
                      <span className="text-sm font-medium text-gray-300">
                        {format(new Date(session.startTime), 'MMM dd, yyyy')}
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {formatDistanceToNow(new Date(session.startTime), { addSuffix: true })}
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>
                      {format(new Date(session.startTime), 'HH:mm')} - {format(new Date(session.endTime), 'HH:mm')}
                    </span>
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-1">
                        <MessageCircle className="h-3 w-3" />
                        <span>{session.messageCount} messages</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Clock className="h-3 w-3" />
                        <span>{session.duration}m</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-2 text-xs text-gray-500 font-mono truncate">
                    Session ID: {session.sessionId.split('_').pop()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
