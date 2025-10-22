"""
Writing Style Trainer Module
Analyzes past newsletters to learn user's writing style and voice
"""
from typing import List, Dict
import re
from collections import Counter

def analyze_writing_style(past_newsletters: List[str]) -> Dict:
    """
    Analyze writing style from past newsletters
    Returns style profile for AI prompt customization
    """
    if not past_newsletters or len(past_newsletters) < 3:
        return {
            "status": "insufficient_data",
            "message": "Please provide at least 3 past newsletters for style analysis"
        }
    
    # Combine all newsletters
    combined_text = " ".join(past_newsletters)
    
    # Analyze style characteristics
    style_profile = {
        "avg_sentence_length": calculate_avg_sentence_length(combined_text),
        "vocabulary_richness": calculate_vocabulary_richness(combined_text),
        "tone_indicators": detect_tone_indicators(combined_text),
        "common_phrases": extract_common_phrases(combined_text),
        "sentence_starters": extract_sentence_starters(past_newsletters),
        "punctuation_style": analyze_punctuation(combined_text),
        "paragraph_structure": analyze_paragraph_structure(past_newsletters),
        "sample_count": len(past_newsletters),
        "total_word_count": len(combined_text.split())
    }
    
    return style_profile

def calculate_avg_sentence_length(text: str) -> float:
    """Calculate average sentence length"""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return 0.0
    
    word_counts = [len(s.split()) for s in sentences]
    return round(sum(word_counts) / len(word_counts), 1)

def calculate_vocabulary_richness(text: str) -> float:
    """Calculate vocabulary richness (unique words / total words)"""
    words = re.findall(r'\b\w+\b', text.lower())
    
    if not words:
        return 0.0
    
    unique_words = len(set(words))
    total_words = len(words)
    
    return round(unique_words / total_words, 2)

def detect_tone_indicators(text: str) -> Dict:
    """Detect tone indicators in the text"""
    text_lower = text.lower()
    
    # Define tone indicators
    tone_patterns = {
        "casual": [r'\byou\b', r'\byour\b', r"let's", r'\bguy', r'\bfolks\b', r'\bhey\b'],
        "professional": [r'\bmoreover\b', r'\btherefore\b', r'\bhowever\b', r'\bfurthermore\b'],
        "enthusiastic": [r'!', r'\bamazing\b', r'\bexciting\b', r'\bincredible\b', r'\blove\b'],
        "analytical": [r'\bdata\b', r'\banalysis\b', r'\bresearch\b', r'\bstudy\b', r'\bshows\b']
    }
    
    tone_scores = {}
    for tone, patterns in tone_patterns.items():
        count = sum(len(re.findall(pattern, text_lower)) for pattern in patterns)
        tone_scores[tone] = count
    
    # Find dominant tone
    if tone_scores:
        dominant_tone = max(tone_scores, key=tone_scores.get)
        return {
            "dominant_tone": dominant_tone,
            "scores": tone_scores
        }
    
    return {"dominant_tone": "neutral", "scores": {}}

def extract_common_phrases(text: str, top_n: int = 10) -> List[str]:
    """Extract most common 2-3 word phrases"""
    # Clean and tokenize
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Extract 2-word phrases
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
    
    # Extract 3-word phrases
    trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)]
    
    # Count and filter
    all_phrases = bigrams + trigrams
    phrase_counts = Counter(all_phrases)
    
    # Filter out common stop phrases
    stop_phrases = {'of the', 'in the', 'to the', 'on the', 'for the', 'and the', 'is a', 'to be'}
    filtered_phrases = {p: c for p, c in phrase_counts.items() if p not in stop_phrases and c > 1}
    
    # Return top N
    return [phrase for phrase, _ in sorted(filtered_phrases.items(), key=lambda x: x[1], reverse=True)[:top_n]]

def extract_sentence_starters(newsletters: List[str], top_n: int = 10) -> List[str]:
    """Extract common sentence starters"""
    starters = []
    
    for newsletter in newsletters:
        sentences = re.split(r'[.!?]+', newsletter)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Get first 2-3 words
                words = sentence.split()[:3]
                if len(words) >= 2:
                    starter = ' '.join(words[:2])
                    starters.append(starter)
    
    # Count and return top
    starter_counts = Counter(starters)
    return [starter for starter, _ in starter_counts.most_common(top_n)]

def analyze_punctuation(text: str) -> Dict:
    """Analyze punctuation usage patterns"""
    punctuation_counts = {
        "exclamation": text.count('!'),
        "question": text.count('?'),
        "em_dash": text.count('—') + text.count('--'),
        "ellipsis": text.count('...'),
        "semicolon": text.count(';'),
        "colon": text.count(':')
    }
    
    total_sentences = len(re.split(r'[.!?]+', text))
    
    return {
        "counts": punctuation_counts,
        "avg_per_sentence": {k: round(v / max(total_sentences, 1), 2) for k, v in punctuation_counts.items()}
    }

def analyze_paragraph_structure(newsletters: List[str]) -> Dict:
    """Analyze paragraph structure patterns"""
    paragraph_lengths = []
    
    for newsletter in newsletters:
        paragraphs = [p.strip() for p in newsletter.split('\n\n') if p.strip()]
        for para in paragraphs:
            sentences = re.split(r'[.!?]+', para)
            sentences = [s.strip() for s in sentences if s.strip()]
            paragraph_lengths.append(len(sentences))
    
    if not paragraph_lengths:
        return {"avg_sentences_per_paragraph": 0, "typical_structure": "unknown"}
    
    avg_length = sum(paragraph_lengths) / len(paragraph_lengths)
    
    if avg_length <= 2:
        structure = "short_punchy"
    elif avg_length <= 4:
        structure = "medium_balanced"
    else:
        structure = "long_detailed"
    
    return {
        "avg_sentences_per_paragraph": round(avg_length, 1),
        "typical_structure": structure
    }

def generate_style_prompt(style_profile: Dict) -> str:
    """Generate AI prompt based on style profile"""
    if style_profile.get("status") == "insufficient_data":
        return ""
    
    tone = style_profile["tone_indicators"]["dominant_tone"]
    avg_sentence_length = style_profile["avg_sentence_length"]
    structure = style_profile["paragraph_structure"]["typical_structure"]
    
    # Build custom prompt
    prompt_parts = []
    
    # Tone guidance
    tone_guidance = {
        "casual": "Write in a friendly, conversational tone. Use 'you' and casual language.",
        "professional": "Write in a professional, business-appropriate tone. Use formal language.",
        "enthusiastic": "Write with enthusiasm and energy. Use exclamation points sparingly but show excitement.",
        "analytical": "Write in an analytical, data-driven tone. Focus on facts and insights."
    }
    prompt_parts.append(tone_guidance.get(tone, "Write in a clear, engaging tone."))
    
    # Sentence length guidance
    if avg_sentence_length < 12:
        prompt_parts.append("Keep sentences short and punchy (under 15 words).")
    elif avg_sentence_length < 20:
        prompt_parts.append("Use medium-length sentences (15-20 words) for readability.")
    else:
        prompt_parts.append("Use detailed, comprehensive sentences when appropriate.")
    
    # Structure guidance
    structure_guidance = {
        "short_punchy": "Keep paragraphs brief (1-2 sentences). Make it scannable.",
        "medium_balanced": "Use balanced paragraphs (3-4 sentences). Mix short and medium lengths.",
        "long_detailed": "Write detailed paragraphs when needed. Dive deep into topics."
    }
    prompt_parts.append(structure_guidance.get(structure, "Use balanced paragraph structure."))
    
    # Common phrases (if any)
    if style_profile["common_phrases"]:
        top_phrases = style_profile["common_phrases"][:3]
        prompt_parts.append(f"Consider using phrases like: {', '.join(top_phrases)}.")
    
    return " ".join(prompt_parts)

def save_style_profile(user_id: str, style_profile: Dict) -> bool:
    """Save style profile to database"""
    from supabase_client import get_supabase_client
    from datetime import datetime, UTC
    import json
    
    try:
        supabase = get_supabase_client()
        
        # Generate custom prompt
        custom_prompt = generate_style_prompt(style_profile)
        
        # Prepare data - make sure style_profile is proper dict, not string
        profile_data = {
            "user_id": user_id,
            "style_profile": style_profile,  # Supabase handles JSONB automatically
            "custom_prompt": custom_prompt,
            "updated_at": datetime.now(UTC).isoformat()
        }
        
        print(f"📝 Attempting to save style profile for user {user_id}")
        print(f"📊 Profile data keys: {profile_data.keys()}")
        
        # Upsert (insert or update) with on_conflict parameter
        response = supabase.table("user_style_profiles").upsert(
            profile_data,
            on_conflict="user_id"
        ).execute()
        
        if response.data:
            print(f"✅ Style profile saved successfully!")
            return True
        else:
            print(f"❌ No data returned from upsert")
            return False
            
    except Exception as e:
        print(f"❌ Error saving style profile: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_style_profile(user_id: str) -> Dict:
    """Get saved style profile from database"""
    from supabase_client import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("user_style_profiles").select("*").eq("user_id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            profile_data = response.data[0]
            
            # ⭐ FIX: Supabase already returns JSONB as dict, don't parse again
            style_profile = profile_data.get("style_profile", {})
            
            # If it's a string (shouldn't be), then parse it
            if isinstance(style_profile, str):
                import json
                style_profile = json.loads(style_profile)
            
            return {
                "style_profile": style_profile,
                "custom_prompt": profile_data.get("custom_prompt", "")
            }
        else:
            # No profile found - return None without error
            return None
    except Exception as e:
        print(f"Error fetching style profile: {e}")
        import traceback
        traceback.print_exc()
        return None