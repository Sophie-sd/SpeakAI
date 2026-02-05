"""
Custom validators for JSON fields
"""
from django.core.exceptions import ValidationError


def validate_homework_instructions(value):
    """
    Валідація структури homework_instructions
    Required: criteria, min_passing_score, feedback_language
    """
    if not isinstance(value, dict):
        raise ValidationError("Must be a dictionary")
    
    # Required fields
    required_fields = ['criteria', 'min_passing_score', 'feedback_language']
    for field in required_fields:
        if field not in value:
            raise ValidationError(f"Missing required field: '{field}'")
    
    criteria = value['criteria']
    if not isinstance(criteria, dict):
        raise ValidationError("'criteria' must be a dictionary")
    
    if len(criteria) == 0:
        raise ValidationError("'criteria' cannot be empty")
    
    # Validate total weight = 100
    total_weight = sum(c.get('weight', 0) for c in criteria.values())
    if not (99 <= total_weight <= 101):  # Allow 1% tolerance
        raise ValidationError(f"Total criteria weight must be 100, got {total_weight}")
    
    # Validate each criterion structure
    for key, criterion in criteria.items():
        if not isinstance(criterion, dict):
            raise ValidationError(f"Criterion '{key}' must be a dictionary")
        
        if 'weight' not in criterion:
            raise ValidationError(f"Criterion '{key}' must have 'weight'")
        
        if 'description' not in criterion:
            raise ValidationError(f"Criterion '{key}' must have 'description'")
        
        # Validate weight is numeric and positive
        try:
            weight = float(criterion['weight'])
            if weight <= 0:
                raise ValidationError(f"Criterion '{key}' weight must be positive")
        except (ValueError, TypeError):
            raise ValidationError(f"Criterion '{key}' weight must be a number")
    
    # Validate min_passing_score
    try:
        min_score = float(value['min_passing_score'])
        if not (0 <= min_score <= 10):
            raise ValidationError("min_passing_score must be between 0 and 10")
    except (ValueError, TypeError):
        raise ValidationError("min_passing_score must be a number")
    
    # Validate feedback_language
    valid_languages = ['ukrainian', 'english', 'both']
    if value['feedback_language'] not in valid_languages:
        raise ValidationError(
            f"feedback_language must be one of: {', '.join(valid_languages)}"
        )


def validate_role_play_scenario(value):
    """
    Валідація структури role_play_scenario
    Required: setting, ai_role, user_role, objectives
    """
    if not isinstance(value, dict):
        raise ValidationError("Must be a dictionary")
    
    required_fields = ['setting', 'ai_role', 'user_role', 'objectives']
    
    for field in required_fields:
        if field not in value:
            raise ValidationError(f"Missing required field: '{field}'")
    
    # Validate setting
    if not isinstance(value['setting'], str) or not value['setting'].strip():
        raise ValidationError("'setting' must be a non-empty string")
    
    # Validate roles
    if not isinstance(value['ai_role'], str) or not value['ai_role'].strip():
        raise ValidationError("'ai_role' must be a non-empty string")
    
    if not isinstance(value['user_role'], str) or not value['user_role'].strip():
        raise ValidationError("'user_role' must be a non-empty string")
    
    # Validate objectives
    if not isinstance(value['objectives'], list):
        raise ValidationError("'objectives' must be a list")
    
    if len(value['objectives']) == 0:
        raise ValidationError("'objectives' cannot be empty")
    
    for i, objective in enumerate(value['objectives']):
        if not isinstance(objective, str) or not objective.strip():
            raise ValidationError(f"Objective {i+1} must be a non-empty string")
    
    # Optional difficulty validation
    if 'difficulty' in value:
        valid_difficulties = ['easy', 'medium', 'hard']
        if value['difficulty'] not in valid_difficulties:
            raise ValidationError(
                f"'difficulty' must be one of: {', '.join(valid_difficulties)}"
            )


def validate_voice_practice_prompts(value):
    """Валідація voice_practice_prompts"""
    if not isinstance(value, list):
        raise ValidationError("Must be a list")
    
    if len(value) == 0:
        raise ValidationError("Cannot be empty list")
    
    for i, prompt in enumerate(value):
        if not isinstance(prompt, str):
            raise ValidationError(f"Prompt {i+1} must be a string")
        
        if not prompt.strip():
            raise ValidationError(f"Prompt {i+1} cannot be empty")
        
        # Validate minimum length
        if len(prompt.strip()) < 5:
            raise ValidationError(f"Prompt {i+1} is too short (minimum 5 characters)")


def validate_learning_objectives(value):
    """
    Валідація learning_objectives для модулів
    """
    if not isinstance(value, list):
        raise ValidationError("Must be a list")
    
    if len(value) == 0:
        raise ValidationError("Cannot be empty list")
    
    for i, objective in enumerate(value):
        if not isinstance(objective, str) or not objective.strip():
            raise ValidationError(f"Objective {i+1} must be a non-empty string")


def validate_vocabulary_list(value):
    """
    Валідація vocabulary_list для уроків
    """
    if not isinstance(value, list):
        raise ValidationError("Must be a list")
    
    for i, word in enumerate(value):
        if not isinstance(word, str):
            raise ValidationError(f"Word {i+1} must be a string")
        
        if not word.strip():
            raise ValidationError(f"Word {i+1} cannot be empty")
        
        # Check for valid word format (letters, spaces, hyphens, apostrophes)
        import re
        if not re.match(r"^[a-zA-Z\s\-']+$", word):
            raise ValidationError(
                f"Word {i+1} '{word}' contains invalid characters. "
                "Only letters, spaces, hyphens, and apostrophes are allowed"
            )
