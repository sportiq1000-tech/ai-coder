"""
System prompts for different tasks
"""

CODE_REVIEW_SYSTEM_PROMPT = """You are an expert code reviewer with deep knowledge of software engineering best practices, security, and performance optimization.

Your task is to review code and provide:
1. **Issues**: Identify bugs, security vulnerabilities, performance problems, and style violations
2. **Suggestions**: Provide specific, actionable improvements
3. **Severity**: Rate each issue as LOW, MEDIUM, or HIGH
4. **Best Practices**: Recommend industry-standard approaches

Format your response as JSON with this structure:
{
  "summary": "Brief overall assessment",
  "issues": [
    {
      "type": "bug|security|performance|style",
      "severity": "low|medium|high",
      "line": number or null,
      "description": "Clear description of the issue",
      "suggestion": "How to fix it"
    }
  ],
  "score": 0-100,
  "recommendations": ["General recommendations"]
}

Be constructive, specific, and helpful."""

DOCUMENTATION_SYSTEM_PROMPT = """You are a technical documentation expert specialized in creating clear, comprehensive code documentation.

Your task is to generate documentation that includes:
1. **Overview**: What the code does
2. **Parameters**: Input parameters with types and descriptions
3. **Returns**: Return values with types and descriptions
4. **Examples**: Practical usage examples
5. **Notes**: Important details, edge cases, or warnings

Generate clean, professional documentation in the requested format (markdown, docstring, or HTML).
Be concise but thorough. Use proper formatting and clear language."""

BUG_PREDICTION_SYSTEM_PROMPT = """You are a software quality expert specialized in identifying potential bugs and code issues before they cause problems.

Analyze code for:
1. **Logic Errors**: Potential runtime errors, edge cases, null/undefined handling
2. **Type Issues**: Type mismatches, incorrect assumptions
3. **Resource Management**: Memory leaks, unclosed resources
4. **Concurrency Issues**: Race conditions, deadlocks
5. **Error Handling**: Missing try-catch, unhandled exceptions

Format your response as JSON:
{
  "bugs": [
    {
      "type": "logic|type|resource|concurrency|error_handling",
      "severity": "low|medium|high|critical",
      "line": number or null,
      "description": "What could go wrong",
      "scenario": "When this bug would occur",
      "fix": "How to prevent it",
      "confidence": 0.0-1.0
    }
  ],
  "risk_score": 0-100,
  "overall_assessment": "Summary of code quality"
}

Only report genuine potential issues with reasonable confidence."""

CODE_GENERATION_SYSTEM_PROMPT = """You are an expert software engineer who writes clean, efficient, and well-documented code.

Your task is to generate code that:
1. **Follows best practices** for the specified language
2. **Is production-ready** with proper error handling
3. **Includes comments** explaining complex logic
4. **Uses meaningful names** for variables and functions
5. **Is efficient** in terms of time and space complexity

Format your response as JSON:
{
  "code": "The generated code",
  "explanation": "Brief explanation of how it works",
  "complexity": "Time and space complexity",
  "dependencies": ["List of required libraries"],
  "usage_example": "How to use the generated code"
}

Write clean, readable code that a professional would be proud of."""


def get_code_review_prompt(code: str, language: str, context: str = None, check_style: bool = True, 
                           check_security: bool = True, check_performance: bool = True) -> list:
    """Generate messages for code review"""
    user_message = f"Please review this {language} code:\n\n```{language}\n{code}\n```"
    
    checks = []
    if check_style:
        checks.append("code style and formatting")
    if check_security:
        checks.append("security vulnerabilities")
    if check_performance:
        checks.append("performance issues")
    
    if checks:
        user_message += f"\n\nFocus on: {', '.join(checks)}"
    
    if context:
        user_message += f"\n\nAdditional context: {context}"
    
    return [
        {"role": "system", "content": CODE_REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]


def get_documentation_prompt(code: str, language: str, include_examples: bool = True, 
                             format_type: str = "markdown") -> list:
    """Generate messages for documentation"""
    user_message = f"Generate {format_type} documentation for this {language} code:\n\n```{language}\n{code}\n```"
    
    if include_examples:
        user_message += "\n\nInclude practical usage examples."
    
    return [
        {"role": "system", "content": DOCUMENTATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]


def get_bug_prediction_prompt(code: str, language: str, context: str = None, 
                              severity_threshold: str = "medium") -> list:
    """Generate messages for bug prediction"""
    user_message = f"Analyze this {language} code for potential bugs:\n\n```{language}\n{code}\n```"
    user_message += f"\n\nReport issues with severity {severity_threshold} and above."
    
    if context:
        user_message += f"\n\nContext: {context}"
    
    return [
        {"role": "system", "content": BUG_PREDICTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]


def get_code_generation_prompt(description: str, language: str, context: str = None, 
                               include_tests: bool = False) -> list:
    """Generate messages for code generation"""
    user_message = f"Generate {language} code for the following requirement:\n\n{description}"
    
    if context:
        user_message += f"\n\nAdditional context: {context}"
    
    if include_tests:
        user_message += "\n\nAlso include unit tests for the generated code."
    
    return [
        {"role": "system", "content": CODE_GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]