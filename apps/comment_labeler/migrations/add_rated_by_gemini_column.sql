-- Add rated_by_gemini column to comment_labels table
ALTER TABLE public.comment_labels
ADD COLUMN IF NOT EXISTS rated_by_gemini BOOLEAN DEFAULT FALSE;

-- Update existing records (all current labels were created by Gemini)
UPDATE public.comment_labels
SET rated_by_gemini = TRUE
WHERE rated_by_gemini IS NULL OR rated_by_gemini = FALSE;

-- Also update to add reasoning column if it doesn't exist (Gemini labels have reasoning)
ALTER TABLE public.comment_labels
ADD COLUMN IF NOT EXISTS reasoning TEXT;

-- Verify the changes
SELECT 
    rated_by_gemini,
    COUNT(*) as count,
    COUNT(reasoning) FILTER (WHERE reasoning IS NOT NULL AND reasoning != '') as with_reasoning
FROM public.comment_labels
GROUP BY rated_by_gemini;
