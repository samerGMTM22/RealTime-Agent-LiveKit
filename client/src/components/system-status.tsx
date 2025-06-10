import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface SystemStatusProps {
  status?: {
    livekit: string;
    openai: string;
    youtube: string;
    latency: string;
    timestamp: string;
  };
}

export default function SystemStatus({ status }: SystemStatusProps) {
  const getStatusColor = (statusValue: string) => {
    switch (statusValue) {
      case 'online':
      case 'connected':
      case 'active':
        return 'text-green-400 bg-green-400';
      case 'offline':
      case 'disconnected':
      case 'inactive':
        return 'text-red-400 bg-red-400';
      case 'error':
        return 'text-red-500 bg-red-500';
      default:
        return 'text-yellow-400 bg-yellow-400';
    }
  };

  const getStatusLabel = (statusValue: string) => {
    switch (statusValue) {
      case 'online':
        return 'Online';
      case 'connected':
        return 'Connected';
      case 'active':
        return 'Active';
      case 'offline':
        return 'Offline';
      case 'disconnected':
        return 'Disconnected';
      case 'inactive':
        return 'Inactive';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  return (
    <Card className="glass-card rounded-2xl premium-shadow">
      <CardHeader>
        <CardTitle className="flex items-center text-xl font-semibold">
          <TrendingUp className="text-green-400 mr-3" />
          System Status
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!status ? (
          <div className="text-center text-gray-400 py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-electric-blue mx-auto mb-2"></div>
            <p className="text-sm">Loading system status...</p>
          </div>
        ) : (
          <>
            {/* LiveKit Connection */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">LiveKit Connection</span>
              <div className="flex items-center space-x-2">
                <div className={cn(
                  "w-2 h-2 rounded-full animate-pulse",
                  getStatusColor(status.livekit).split(' ')[1]
                )}></div>
                <span className={cn(
                  "text-sm font-medium",
                  getStatusColor(status.livekit).split(' ')[0]
                )}>
                  {getStatusLabel(status.livekit)}
                </span>
              </div>
            </div>
            
            {/* OpenAI API */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">OpenAI API</span>
              <div className="flex items-center space-x-2">
                <div className={cn(
                  "w-2 h-2 rounded-full animate-pulse",
                  getStatusColor(status.openai).split(' ')[1]
                )}></div>
                <span className={cn(
                  "text-sm font-medium",
                  getStatusColor(status.openai).split(' ')[0]
                )}>
                  {getStatusLabel(status.openai)}
                </span>
              </div>
            </div>
            
            {/* YouTube API */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">YouTube API</span>
              <div className="flex items-center space-x-2">
                <div className={cn(
                  "w-2 h-2 rounded-full animate-pulse",
                  getStatusColor(status.youtube).split(' ')[1]
                )}></div>
                <span className={cn(
                  "text-sm font-medium",
                  getStatusColor(status.youtube).split(' ')[0]
                )}>
                  {getStatusLabel(status.youtube)}
                </span>
              </div>
            </div>
            
            {/* Audio Latency */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Audio Latency</span>
              <span className="text-sm font-medium text-cyber-cyan">{status.latency}</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
