import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageCircle, User, Bot } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface ConversationHistoryProps {
  sessionId: string;
}

export default function ConversationHistory({ sessionId }: ConversationHistoryProps) {
  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ["/api/conversations", sessionId],
    enabled: !!sessionId,
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
          <MessageCircle className="text-cyber-cyan mr-3" />
          Conversation History
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96 pr-4">
          {conversations.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              <MessageCircle className="mx-auto h-12 w-12 text-gray-600 mb-4" />
              <p>No conversations yet</p>
              <p className="text-sm">Start a voice session to see conversations here</p>
            </div>
          ) : (
            <div className="space-y-4">
              {conversations.map((conversation: any) => (
                <div key={conversation.id} className="space-y-3">
                  {/* User Message */}
                  {conversation.userMessage && (
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                        <User className="text-xs" />
                      </div>
                      <div className="glass-card p-3 rounded-lg flex-1">
                        <p className="text-sm">{conversation.userMessage}</p>
                        <span className="text-xs text-gray-400">
                          {formatDistanceToNow(new Date(conversation.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                  )}
                  
                  {/* Agent Response */}
                  {conversation.agentResponse && (
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-r from-electric-blue to-cyber-cyan flex items-center justify-center flex-shrink-0">
                        <Bot className="text-xs" />
                      </div>
                      <div className="glass-card p-3 rounded-lg flex-1">
                        <p className="text-sm">{conversation.agentResponse}</p>
                        <span className="text-xs text-gray-400">
                          {formatDistanceToNow(new Date(conversation.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
