import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Globe, User, ArrowRight } from "lucide-react";

// Supported languages from backend translation service
const SUPPORTED_LANGUAGES = {
  "en": "English",
  "es": "Spanish", 
  "fr": "French",
  "de": "German",
  "it": "Italian",
  "pt": "Portuguese",
  "ru": "Russian",
  "ja": "Japanese",
  "ko": "Korean",
  "zh": "Chinese",
  "ar": "Arabic",
  "hi": "Hindi",
  "bn": "Bengali",
  "ur": "Urdu",
  "tr": "Turkish",
  "nl": "Dutch",
  "pl": "Polish",
  "sv": "Swedish",
  "da": "Danish",
  "no": "Norwegian",
  "fi": "Finnish",
  "cs": "Czech",
  "sk": "Slovak",
  "hu": "Hungarian",
  "ro": "Romanian",
  "bg": "Bulgarian",
  "hr": "Croatian",
  "sr": "Serbian",
  "sl": "Slovenian",
  "et": "Estonian",
  "lv": "Latvian",
  "lt": "Lithuanian",
  "mt": "Maltese",
  "el": "Greek",
  "he": "Hebrew",
  "th": "Thai",
  "vi": "Vietnamese",
  "id": "Indonesian",
  "ms": "Malay",
  "tl": "Filipino",
  "sw": "Swahili",
  "af": "Afrikaans",
  "is": "Icelandic",
  "ga": "Irish",
  "cy": "Welsh",
  "eu": "Basque",
  "ca": "Catalan",
  "gl": "Galician",
  "mk": "Macedonian",
  "sq": "Albanian",
  "bs": "Bosnian",
  "me": "Montenegrin",
  "ky": "Kyrgyz",
  "kk": "Kazakh",
  "uz": "Uzbek",
  "tg": "Tajik",
  "mn": "Mongolian",
  "ka": "Georgian",
  "hy": "Armenian",
  "az": "Azerbaijani",
  "fa": "Persian",
  "ps": "Pashto",
  "ku": "Kurdish",
  "yi": "Yiddish",
  "am": "Amharic"
};

interface UserPreferences {
  displayName: string;
  preferredLanguage: string;
}

interface UserOnboardingProps {
  roomId: string;
  onComplete: (preferences: UserPreferences) => void;
  onBack: () => void;
}

export const UserOnboarding = ({ roomId, onComplete, onBack }: UserOnboardingProps) => {
  const [displayName, setDisplayName] = useState("");
  const [preferredLanguage, setPreferredLanguage] = useState("en");
  const [errors, setErrors] = useState<{ displayName?: string; preferredLanguage?: string }>({});

  // Load saved preferences if available
  useEffect(() => {
    const savedPreferences = localStorage.getItem(`chat_preferences_${roomId}`);
    if (savedPreferences) {
      try {
        const preferences = JSON.parse(savedPreferences);
        setDisplayName(preferences.displayName || "");
        setPreferredLanguage(preferences.preferredLanguage || "en");
      } catch (error) {
        console.warn("Failed to load saved preferences:", error);
      }
    }
  }, [roomId]);

  const validateForm = (): boolean => {
    const newErrors: { displayName?: string; preferredLanguage?: string } = {};

    if (!displayName.trim()) {
      newErrors.displayName = "Please enter your name";
    } else if (displayName.trim().length < 2) {
      newErrors.displayName = "Name must be at least 2 characters";
    } else if (displayName.trim().length > 50) {
      newErrors.displayName = "Name must be less than 50 characters";
    }

    if (!preferredLanguage) {
      newErrors.preferredLanguage = "Please select your preferred language";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    const preferences: UserPreferences = {
      displayName: displayName.trim(),
      preferredLanguage
    };

    // Save preferences to localStorage
    localStorage.setItem(`chat_preferences_${roomId}`, JSON.stringify(preferences));
    
    // Call the completion handler
    onComplete(preferences);
  };

  const handleLanguageChange = (value: string) => {
    setPreferredLanguage(value);
    if (errors.preferredLanguage) {
      setErrors(prev => ({ ...prev, preferredLanguage: undefined }));
    }
  };

  const handleNameChange = (value: string) => {
    setDisplayName(value);
    if (errors.displayName) {
      setErrors(prev => ({ ...prev, displayName: undefined }));
    }
  };

  return (
    <div className="min-h-screen bg-chat-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-primary rounded-full">
              <Globe className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl">Join Chat Room</CardTitle>
          <CardDescription>
            Set your preferences to get started with multilingual chat
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Display Name Input */}
            <div className="space-y-2">
              <Label htmlFor="displayName" className="flex items-center gap-2">
                <User className="h-4 w-4" />
                Your Name
              </Label>
              <Input
                id="displayName"
                type="text"
                placeholder="Enter your name"
                value={displayName}
                onChange={(e) => handleNameChange(e.target.value)}
                className={errors.displayName ? "border-destructive" : ""}
                maxLength={50}
              />
              {errors.displayName && (
                <p className="text-sm text-destructive">{errors.displayName}</p>
              )}
              <p className="text-xs text-muted-foreground">
                This name will be visible to other users in the chat room
              </p>
            </div>

            {/* Language Selection */}
            <div className="space-y-2">
              <Label htmlFor="preferredLanguage" className="flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Preferred Language
              </Label>
              <Select value={preferredLanguage} onValueChange={handleLanguageChange}>
                <SelectTrigger className={errors.preferredLanguage ? "border-destructive" : ""}>
                  <SelectValue placeholder="Select your preferred language" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(SUPPORTED_LANGUAGES).map(([code, name]) => (
                    <SelectItem key={code} value={code}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.preferredLanguage && (
                <p className="text-sm text-destructive">{errors.preferredLanguage}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Messages will be translated to your preferred language
              </p>
            </div>

            {/* Room Info */}
            <div className="p-3 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                <strong>Room ID:</strong> {roomId}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                You can share this room ID with others to invite them to chat
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={onBack}
                className="flex-1"
              >
                Back
              </Button>
              <Button
                type="submit"
                className="flex-1"
                disabled={!displayName.trim() || !preferredLanguage}
              >
                Join Chat
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
