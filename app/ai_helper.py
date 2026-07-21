from openai import OpenAI
import os
import re
import random
from collections import Counter


client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def answer_question(query, documents):
    """
    Use GPT to answer questions based on uploaded documents
    """
    if not documents:
        return "I don't have any documents to reference. Please upload some study materials first."
    

    context = "\n\n".join([
        f"Document: {doc.original_filename}\nContent: {doc.content[:3000]}"
        for doc in documents[:5] 
    ])
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful study assistant. Answer questions based ONLY on the provided documents. If the answer isn't in the documents, say so. Be concise but informative."
                },
                {
                    "role": "user",
                    "content": f"Documents:\n{context}\n\nQuestion: {query}"
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return answer_question_fallback(query, documents)

def answer_question_fallback(query, documents):
    """
    Fallback method if API fails
    """
    query_lower = query.lower()
    query_words = set(re.findall(r'\w+', query_lower))
    
    results = []
    
    for doc in documents:
        content_lower = doc.content.lower()
        sentences = [s.strip() for s in doc.content.split('.') if len(s.strip()) > 20]
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            matches = sum(1 for word in query_words if word in sentence_lower)
            if matches > 0:
                results.append((sentence, matches))
    
    if not results:
        return "I couldn't find relevant information in your documents."
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results[0][0]

def generate_quiz(documents, num_questions=5, difficulty="medium"):
    """
    Generate quiz using GPT-3.5
    """
    if not documents:
        return []
    
    # Combine content from all documents
    combined_content = "\n\n".join([
        f"{doc.original_filename}:\n{doc.content[:2000]}"
        for doc in documents[:3]
    ])
    
    # Truncate if too long
    if len(combined_content) > 6000:
        combined_content = combined_content[:6000]
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a quiz generator. Create {num_questions} multiple-choice questions from the study material.

STRICT FORMAT REQUIREMENTS:
- Each question MUST follow this EXACT format
- No extra text, no explanations
- Just questions in this format:

Question 1: [clear question text]
A) [option]
B) [option]
C) [option]
D) [option]
Correct Answer: [A/B/C/D]

Question 2: [clear question text]
A) [option]
B) [option]
C) [option]
D) [option]
Correct Answer: [A/B/C/D]

Rules:
- Questions should test understanding, not just memory
- Make wrong answers plausible but clearly incorrect
- Vary difficulty from easy to {difficulty}
- Only use information from the provided material"""
                },
                {
                    "role": "user",
                    "content": f"Study Material:\n\n{combined_content}\n\nGenerate {num_questions} questions now."
                }
            ],
            temperature=0.8,
            max_tokens=1500
        )
        
        generated_text = response.choices[0].message.content
        print(f"GPT Response:\n{generated_text[:500]}...")
        
        questions = parse_gpt_quiz(generated_text, num_questions)
        
        if len(questions) == 0:
            print("Parsing failed, using fallback generator")
            return generate_quiz_fallback(documents, num_questions)
        
        return questions
        
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return generate_quiz_fallback(documents, num_questions)

def parse_gpt_quiz(response_text, expected_count=5):
    """
    FIXED: Parse GPT's quiz response with better regex patterns
    """
    questions = []
    
    try:
        # Split by "Question N:" pattern
        pattern = r'Question \d+:'
        parts = re.split(pattern, response_text)
        parts = [p.strip() for p in parts if p.strip()]
        
        for part in parts[:expected_count]:
            try:
                # Extract question text (everything before first option)
                q_match = re.search(r'^(.+?)(?=\n\s*A\))', part, re.DOTALL)
                if not q_match:
                    continue
                
                question_text = q_match.group(1).strip()
                
                # Extract all options using better pattern
                options = {}
                
                # Pattern for each option: Letter) followed by text until next letter or "Correct Answer:"
                option_pattern = r'([A-D])\)\s*(.+?)(?=\n\s*[A-D]\)|\n\s*Correct Answer:|\Z)'
                matches = re.finditer(option_pattern, part, re.DOTALL)
                
                for match in matches:
                    letter = match.group(1)
                    text = match.group(2).strip()
                    options[letter] = text
                
                # Extract correct answer
                correct_match = re.search(r'Correct Answer:\s*([A-D])', part, re.IGNORECASE)
                if not correct_match:
                    continue
                
                correct_answer = correct_match.group(1).upper()
                
                # Validate we have all 4 options and correct answer
                if question_text and len(options) == 4 and correct_answer in options:
                    questions.append({
                        'text': question_text,
                        'option_a': options['A'],
                        'option_b': options['B'],
                        'option_c': options['C'],
                        'option_d': options['D'],
                        'correct_answer': correct_answer
                    })
            
            except Exception as e:
                print(f"Error parsing question: {e}")
                continue
        
        return questions
    
    except Exception as e:
        print(f"Parse error: {e}")
        return []

def generate_quiz_fallback(documents, num_questions=5):
    """
    Fallback quiz generator
    """
    if not documents:
        return []
    
    all_content = "\n\n".join([doc.content for doc in documents])
    sentences = [s.strip() for s in all_content.split('.') if len(s.strip()) > 30]
    
    if not sentences:
        return []
    
    words = re.findall(r'\b\w{4,}\b', all_content.lower())
    word_freq = Counter(words)
    important_words = [w for w, c in word_freq.most_common(100) if c >= 2]
    
    questions = []
    used = set()
    
    for _ in range(min(num_questions, len(sentences))):
        available = [i for i in range(len(sentences)) if i not in used]
        if not available:
            break
        
        idx = random.choice(available)
        used.add(idx)
        sentence = sentences[idx]
        words_list = sentence.split()
        
        if len(words_list) < 6:
            continue
        
        blank_candidates = []
        for i, word in enumerate(words_list):
            clean = re.sub(r'[^\w]', '', word).lower()
            if len(clean) > 4 and clean in important_words:
                blank_candidates.append((i, word, clean))
        
        if not blank_candidates:
            mid = len(words_list) // 2
            blank_candidates = [(mid, words_list[mid], re.sub(r'[^\w]', '', words_list[mid]).lower())]
        
        blank_idx, blank_word, correct = random.choice(blank_candidates)
        
        q_words = words_list.copy()
        q_words[blank_idx] = '_____'
        question_text = ' '.join(q_words)
        
        wrong = [w for w in important_words if w != correct]
        random.shuffle(wrong)
        wrong = wrong[:3]
        
        if len(wrong) < 3:
            extra = [w for w in word_freq.keys() if w not in wrong and w != correct]
            random.shuffle(extra)
            wrong.extend(extra[:3 - len(wrong)])
        
        if len(wrong) < 3:
            continue
        
        all_opts = [correct] + wrong[:3]
        random.shuffle(all_opts)
        
        correct_letter = ['A', 'B', 'C', 'D'][all_opts.index(correct)]
        
        questions.append({
            'text': f"Fill in the blank: {question_text}",
            'option_a': all_opts[0],
            'option_b': all_opts[1],
            'option_c': all_opts[2],
            'option_d': all_opts[3],
            'correct_answer': correct_letter
        })
    
    return questions