import { useState, useEffect, useRef } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { ScrollArea } from "../../components/ui/scroll-area";
import { conversationAPI, customerAPI } from "../../lib/api";
import { toast } from "sonner";
import { Search, Send, Phone, MessageSquare, User, Bot, Clock, PhoneIncoming, PhoneOutgoing, RefreshCw, Plus } from "lucide-react";
import { cn } from "../../lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState([]);
  const [selectedConv, setSelectedConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [search, setSearch] = useState("");
  const [showNewConvDialog, setShowNewConvDialog] = useState(false);
  const [customers, setCustomers] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchConversations();
    fetchCustomers();
    // Poll for new messages every 15 seconds
    const interval = setInterval(fetchConversations, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await customerAPI.list();
      setCustomers(response.data);
    } catch (error) {
      console.error("Failed to load customers");
    }
  };

  useEffect(() => {
    if (selectedConv) {
      fetchMessages(selectedConv.id);
    }
  }, [selectedConv]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchConversations = async () => {
    try {
      const response = await conversationAPI.list();
      setConversations(response.data);
      if (response.data.length > 0 && !selectedConv) {
        setSelectedConv(response.data[0]);
      }
    } catch (error) {
      toast.error("Failed to load conversations");
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (convId) => {
    try {
      const response = await conversationAPI.get(convId);
      setMessages(response.data.messages || []);
    } catch (error) {
      toast.error("Failed to load messages");
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConv) return;

    setSending(true);
    try {
      await conversationAPI.sendMessage({
        conversation_id: selectedConv.id,
        customer_id: selectedConv.customer_id,
        direction: "OUTBOUND",
        sender_type: "STAFF",
        channel: "SMS",
        content: newMessage,
      });
      setNewMessage("");
      fetchMessages(selectedConv.id);
      toast.success("Message sent");
    } catch (error) {
      toast.error("Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const filteredConversations = conversations.filter((conv) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      conv.customer?.first_name?.toLowerCase().includes(searchLower) ||
      conv.customer?.last_name?.toLowerCase().includes(searchLower) ||
      conv.customer?.phone?.includes(search)
    );
  });

  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return "Just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const handleStartNewConversation = async (customerId) => {
    // Check if conversation already exists for this customer
    const existing = conversations.find(c => c.customer_id === customerId);
    if (existing) {
      setSelectedConv(existing);
      setShowNewConvDialog(false);
      return;
    }
    
    // For now, we'll just show a toast since we need to send the first message
    // to create the conversation
    const customer = customers.find(c => c.id === customerId);
    if (customer) {
      toast.info(`Select "${customer.first_name} ${customer.last_name}" and send a message to start a conversation`);
    }
    setShowNewConvDialog(false);
  };

  return (
    <Layout title="Inbox" subtitle="SMS conversations with customers">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-12rem)]">
        {/* Conversations List */}
        <Card className="lg:col-span-1 flex flex-col">
          <CardHeader className="pb-3 border-b space-y-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-heading">Conversations</CardTitle>
              <Button size="sm" variant="outline" onClick={() => fetchConversations()}>
                <RefreshCw className="h-3 w-3" />
              </Button>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search conversations..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
                data-testid="conversations-search"
              />
            </div>
          </CardHeader>
          <ScrollArea className="flex-1">
            <div className="p-2">
              {loading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
                </div>
              ) : filteredConversations.length === 0 ? (
                <p className="text-center text-muted-foreground py-8 text-sm">
                  No conversations yet
                </p>
              ) : (
                filteredConversations.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conversation={conv}
                    isSelected={selectedConv?.id === conv.id}
                    onClick={() => setSelectedConv(conv)}
                    formatTime={formatTime}
                  />
                ))
              )}
            </div>
          </ScrollArea>
        </Card>

        {/* Messages Area */}
        <Card className="lg:col-span-2 flex flex-col">
          {selectedConv ? (
            <>
              {/* Header */}
              <CardHeader className="pb-3 border-b">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                      <User className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base font-heading">
                        {selectedConv.customer?.first_name} {selectedConv.customer?.last_name}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground font-mono">
                        {selectedConv.customer?.phone}
                      </p>
                    </div>
                  </div>
                  <Badge variant={selectedConv.status === "OPEN" ? "default" : "secondary"}>
                    {selectedConv.status}
                  </Badge>
                </div>
              </CardHeader>

              {/* Messages */}
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} formatTime={formatTime} />
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {/* Input */}
              <div className="p-4 border-t">
                <form onSubmit={handleSendMessage} className="flex gap-2">
                  <Input
                    placeholder="Type your message..."
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    className="flex-1"
                    data-testid="message-input"
                  />
                  <Button 
                    type="submit" 
                    disabled={sending || !newMessage.trim()}
                    data-testid="send-message"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a conversation to view messages</p>
              </div>
            </div>
          )}
        </Card>
      </div>
    </Layout>
  );
}

function ConversationItem({ conversation, isSelected, onClick, formatTime }) {
  const senderTypeIcon = {
    CUSTOMER: <User className="h-3 w-3" />,
    AI: <Bot className="h-3 w-3" />,
    STAFF: <User className="h-3 w-3" />,
  };

  return (
    <div
      className={cn(
        "p-3 rounded-md cursor-pointer transition-colors mb-1",
        isSelected ? "bg-primary/10 border border-primary/20" : "hover:bg-muted"
      )}
      onClick={onClick}
      data-testid={`conversation-${conversation.id}`}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-muted rounded-full flex items-center justify-center flex-shrink-0">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <p className="font-medium text-sm truncate">
              {conversation.customer?.first_name} {conversation.customer?.last_name}
            </p>
            <span className="text-xs text-muted-foreground">
              {formatTime(conversation.last_message_at)}
            </span>
          </div>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            {conversation.last_message_from && senderTypeIcon[conversation.last_message_from]}
            <span className="truncate">
              {conversation.last_message_from === "CUSTOMER" ? "Customer" : "You"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message, formatTime }) {
  const isOutbound = message.direction === "OUTBOUND";
  const isAI = message.sender_type === "AI";
  const isSystem = message.sender_type === "SYSTEM";

  if (message.is_call_summary) {
    return (
      <div className="flex justify-center">
        <div className="bg-muted px-4 py-2 rounded-full text-sm text-muted-foreground flex items-center gap-2">
          <Phone className="h-3 w-3" />
          <span>Call Summary: {message.content.substring(0, 50)}...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex", isOutbound ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-lg px-4 py-2",
          isOutbound
            ? isAI
              ? "bg-purple-100 text-purple-900"
              : "bg-primary text-primary-foreground"
            : "bg-muted"
        )}
      >
        {isAI && (
          <div className="flex items-center gap-1 text-xs opacity-75 mb-1">
            <Bot className="h-3 w-3" />
            <span>AI Response</span>
          </div>
        )}
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <div className={cn(
          "flex items-center gap-1 mt-1 text-xs",
          isOutbound ? "text-primary-foreground/70" : "text-muted-foreground"
        )}>
          <Clock className="h-3 w-3" />
          <span>{formatTime(message.created_at)}</span>
        </div>
      </div>
    </div>
  );
}
