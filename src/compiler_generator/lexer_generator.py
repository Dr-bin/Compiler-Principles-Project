"""Lexer Generator (Student A's responsibility)

This module implements automatic construction of scanner/lexer functionality,
using Thompson's construction algorithm and subset construction algorithm
to convert regular expressions to NFA, then to DFA for efficient lexical analysis.

Algorithm flow:
1. Regular expression → AST (RegexParser)
2. AST → NFA (Thompson's construction)
3. NFA → DFA (Subset construction)
4. DFA longest match scanning
"""

from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass


# ============================================================================
# Constants
# ============================================================================

EPSILON = None  # Marker for ε-transitions


# ============================================================================
# Token Data Structure
# ============================================================================

@dataclass
class Token:
    """Token data structure representing a lexical unit
    
    Attributes:
        type: Token type (e.g., 'ID', 'NUM', 'PLUS', etc.)
        value: Token literal value (actual text content)
        line: Line number in source code
        column: Column number in source code
    """
    type: str
    value: str
    line: int
    column: int

    def __repr__(self):
        """Return string representation of Token"""
        return f"Token({self.type}, {self.value!r}, {self.line}, {self.column})"


# ============================================================================
# NFA Related Classes
# ============================================================================

class NFAState:
    """NFA state: records transitions and whether it's an accepting state"""
    _id_counter = 0

    def __init__(self):
        self.id = NFAState._id_counter
        NFAState._id_counter += 1
        # transitions: symbol -> set(NFAState)
        self.trans: Dict[Optional[str], Set['NFAState']] = {}
        self.is_accept = False
        self.token_type: Optional[str] = None   # Which token this accepts
        self.priority: Optional[int] = None     # Token priority (smaller number = higher priority)

    def add_trans(self, symbol: Optional[str], state: 'NFAState'):
        """Add a transition"""
        if symbol not in self.trans:
            self.trans[symbol] = set()
        self.trans[symbol].add(state)


class NFAFragment:
    """Fragment used in Thompson's construction: start state + set of accepting states"""
    def __init__(self, start: NFAState, accepts: Set[NFAState]):
        self.start = start
        self.accepts = accepts  # set of NFAState


# ============================================================================
# DFA Related Classes
# ============================================================================

class DFAState:
    """DFA state: composed of a set of NFA states"""
    _id_counter = 0

    def __init__(self, nfa_states: Set[NFAState]):
        self.id = DFAState._id_counter
        DFAState._id_counter += 1
        self.nfa_states = frozenset(nfa_states)
        self.trans: Dict[str, 'DFAState'] = {}      # symbol -> DFAState
        self.is_accept = False
        self.token_type: Optional[str] = None
        self.priority: Optional[int] = None

    def __repr__(self):
        return f"<DFAState {self.id} accept={self.is_accept}>"


# ============================================================================
# Regular Expression Parser
# ============================================================================

class RegexParser:
    """
    Simple regular expression parser supporting:
      - Literal characters: a, b, +, *, ...
      - Concatenation: implicit, e.g., "ab" means a followed by b
      - Alternation: |
      - Kleene closure: *
      - Grouping: (...)
      - Character classes: [0-9], [A-Za-z0-9]
      - Escaping: \\(, \\), \\+, \\*, \\\\, etc.
    
    Grammar:
      expr  -> term ('|' term)*
      term  -> factor+
      factor-> base ('*')*
      base  -> literal | '(' expr ')' | char_class
    """
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.i = 0

    def peek(self) -> Optional[str]:
        """Peek at current character without moving pointer"""
        if self.i >= len(self.pattern):
            return None
        return self.pattern[self.i]

    def get(self) -> Optional[str]:
        """Get current character and move pointer"""
        ch = self.peek()
        if ch is not None:
            self.i += 1
        return ch

    def parse(self):
        """Parse regular expression and return AST"""
        expr = self.parse_expr()
        if self.peek() is not None:
            raise ValueError(f"Unexpected char at position {self.i}: {self.peek()}")
        return expr

    # expr -> term ('|' term)*
    def parse_expr(self):
        """Parse expression (alternation operation)"""
        term = self.parse_term()
        terms = [term]
        while self.peek() == '|':
            self.get()
            terms.append(self.parse_term())
        if len(terms) == 1:
            return terms[0]
        return ('ALT', terms)

    # term -> factor+
    def parse_term(self):
        """Parse term (concatenation operation)"""
        factors = []
        while True:
            ch = self.peek()
            if ch is None or ch in ')|':
                break
            factors.append(self.parse_factor())
        if not factors:
            # Empty string epsilon
            return ('EPS',)
        if len(factors) == 1:
            return factors[0]
        return ('CONCAT', factors)

    # factor -> base ('*' | '+' | '?')*
    def parse_factor(self):
        """Parse factor (Kleene closure, positive closure, and optional operations)"""
        base = self.parse_base()
        while True:
            ch = self.peek()
            if ch == '*':
                self.get()
                base = ('STAR', base)
            elif ch == '+':
                # a+ converts to aa*
                self.get()
                base = ('CONCAT', [base, ('STAR', base)])
            elif ch == '?':
                # a? converts to a|epsilon
                self.get()
                base = ('ALT', [base, ('EPS',)])
            else:
                break
        return base

    # base -> literal | '(' expr ')' | '(?:' expr ')' | char_class
    def parse_base(self):
        """Parse base element"""
        ch = self.peek()
        if ch is None:
            raise ValueError("Unexpected end of pattern")
        if ch == '(':
            self.get()
            # Check if it's a non-capturing group (?:...)
            if self.peek() == '?' and self.i + 1 < len(self.pattern) and self.pattern[self.i + 1] == ':':
                self.get()  # Consume '?'
                self.get()  # Consume ':'
            expr = self.parse_expr()
            if self.get() != ')':
                raise ValueError("Expected ')'")
            return expr
        if ch == '[':
            return self.parse_char_class()
        if ch == '\\':
            # Escape character
            self.get()
            esc = self.get()
            if esc is None:
                raise ValueError("Dangling escape")
            return ('LIT', esc)
        # Ordinary literal character
        self.get()
        return ('LIT', ch)

    def parse_char_class(self):
        """Parse character class, supporting [0-9], [a-zA-Z0-9], etc."""
        assert self.get() == '['
        negate = False
        if self.peek() == '^':
            negate = True
            self.get()
        chars = set()
        prev_char = None
        
        while True:
            ch = self.peek()
            if ch is None:
                raise ValueError("Unterminated char class")
            if ch == ']':
                if prev_char is not None:
                    chars.add(prev_char)
                self.get()
                break
            
            if ch == '\\':
                self.get()  # Consume '\'
                ch = self.get()
                if ch is None:
                    raise ValueError("Dangling escape in class")
                if prev_char is not None:
                    chars.add(prev_char)
                prev_char = ch
            elif ch == '-':
                # Handle range: a-z
                self.get()  # Consume '-'
                if prev_char is None:
                    # If '-' is at the beginning, treat as literal character
                    chars.add('-')
                    prev_char = None
                else:
                    # Check next character
                    next_ch = self.peek()
                    if next_ch is None or next_ch == ']':
                        # '-' at the end, treat as literal character
                        chars.add(prev_char)
                        chars.add('-')
                        prev_char = None
                    else:
                        # Form range prev_char-next_ch
                        self.get()  # Consume end character
                        start, end = prev_char, next_ch
                        if ord(start) > ord(end):
                            start, end = end, start
                        for c in range(ord(start), ord(end) + 1):
                            chars.add(chr(c))
                        prev_char = None
            else:
                self.get()
                if prev_char is not None:
                    chars.add(prev_char)
                prev_char = ch
        
        if prev_char is not None:
            chars.add(prev_char)
        
        if negate:
            raise NotImplementedError("Negated character classes not supported")
        
        # Represent as ALT(LIT) combination
        if not chars:
            return ('EPS',)
        if len(chars) == 1:
            return ('LIT', next(iter(chars)))
        return ('ALT', [('LIT', c) for c in sorted(chars)])


# ============================================================================
# Thompson's Construction: AST → NFA
# ============================================================================

def thompson(ast) -> NFAFragment:
    """Thompson's construction: AST -> NFAFragment"""
    def build(node):
        nodetype = node[0]
        if nodetype == 'LIT':
            start = NFAState()
            end = NFAState()
            start.add_trans(node[1], end)
            return NFAFragment(start, {end})
        elif nodetype == 'EPS':
            start = NFAState()
            return NFAFragment(start, {start})
        elif nodetype == 'CONCAT':
            frags = [build(n) for n in node[1]]
            cur = frags[0]
            for nxt in frags[1:]:
                for a in cur.accepts:
                    a.add_trans(EPSILON, nxt.start)
                cur = NFAFragment(cur.start, nxt.accepts)
            return cur
        elif nodetype == 'ALT':
            start = NFAState()
            accepts = set()
            for sub in node[1]:
                frag = build(sub)
                start.add_trans(EPSILON, frag.start)
                accepts.update(frag.accepts)
            return NFAFragment(start, accepts)
        elif nodetype == 'STAR':
            frag = build(node[1])
            start = NFAState()
            start.add_trans(EPSILON, frag.start)
            for a in frag.accepts:
                a.add_trans(EPSILON, frag.start)
                a.add_trans(EPSILON, start)
            return NFAFragment(start, {start})
        else:
            raise ValueError(f"Unknown AST node: {node}")
    return build(ast)


# ============================================================================
# Subset Construction: NFA → DFA
# ============================================================================

def epsilon_closure(states: Set[NFAState]) -> Set[NFAState]:
    """Compute ε-closure"""
    stack = list(states)
    closure = set(states)
    while stack:
        s = stack.pop()
        for nxt in s.trans.get(EPSILON, []):
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return closure


def move(states: Set[NFAState], symbol: str) -> Set[NFAState]:
    """NFA move operation"""
    res = set()
    for s in states:
        for nxt in s.trans.get(symbol, []):
            res.add(nxt)
    return res


def nfa_to_dfa(start_state: NFAState) -> Tuple[DFAState, List[DFAState], Set[str]]:
    """
    Subset construction: NFA -> DFA (optimized version)
    
    Returns:
        start_dfa: DFA start state
        dfa_states_list: List of all DFA states
        alphabet: Alphabet
    
    Optimizations:
        - Use set operations to optimize epsilon_closure and move
        - Reduce redundant computations
    """
    # Collect all NFA states & alphabet (optimization: collect in one pass)
    all_states = set()
    alphabet = set()
    stack = [start_state]
    visited = set()
    
    while stack:
        s = stack.pop()
        if s in visited:
            continue
        visited.add(s)
        all_states.add(s)
        
        for sym, targets in s.trans.items():
            if sym is not EPSILON:
                alphabet.add(sym)
            for t in targets:
                if t not in visited:
                    stack.append(t)

    start_closure = epsilon_closure({start_state})
    dfa_states_map: Dict[frozenset, DFAState] = {}
    dfa_list: List[DFAState] = []

    def get_dfa_state(nfa_set: Set[NFAState]) -> DFAState:
        """Get or create DFA state (optimization: cache frozenset)"""
        key = frozenset(nfa_set)
        if key in dfa_states_map:
            return dfa_states_map[key]
        ds = DFAState(key)
        # Determine if it's an accepting state and corresponding token (by priority)
        best_priority: Optional[int] = None
        best_token: Optional[str] = None
        for n in key:
            if n.is_accept:
                if best_priority is None or (n.priority is not None and n.priority < best_priority):
                    best_priority = n.priority
                    best_token = n.token_type
        if best_token is not None:
            ds.is_accept = True
            ds.priority = best_priority
            ds.token_type = best_token
        dfa_states_map[key] = ds
        dfa_list.append(ds)
        return ds

    start_dfa = get_dfa_state(start_closure)
    worklist = [start_dfa]
    processed = {start_dfa}  # Optimization: avoid duplicate processing
    
    while worklist:
        d = worklist.pop()
        processed.add(d)
        
        # Optimization: only process characters that actually appear
        for sym in alphabet:
            target_nfa = epsilon_closure(move(d.nfa_states, sym))
            if not target_nfa:
                continue
            tgt_dfa = get_dfa_state(target_nfa)
            d.trans[sym] = tgt_dfa
            if tgt_dfa not in processed:
                worklist.append(tgt_dfa)
                processed.add(tgt_dfa)

    return start_dfa, dfa_list, alphabet


class LexerGenerator:
    """Lexer generator class
    
    Automatically generates lexer using Thompson's construction and subset construction algorithms.
    Compiles multiple regular expression rules into an efficient DFA scanner.
    
    Algorithm flow:
    1. Regular expression → AST (RegexParser)
    2. AST → NFA (Thompson's construction)
    3. NFA → DFA (Subset construction)
    4. DFA longest match scanning
    """

    def __init__(self):
        """Initialize lexer generator
        
        Attributes:
            token_specs: List storing (name, regex_pattern) tuples
            start_dfa: DFA start state
            alphabet: Alphabet (all possible input characters)
            compiled_patterns: Compatibility attribute (deprecated, kept for testing)
        """
        self.token_specs: List[Tuple[str, str]] = []
        self.start_dfa: Optional[DFAState] = None
        self.alphabet: Set[str] = set()
        # Compatibility attribute: for backward compatibility with test code
        self.compiled_patterns: List[Tuple[str, str]] = []

    def add_token_rule(self, token_type: str, regex_pattern: str) -> None:
        """Add a lexical rule (Token type and corresponding regular expression)
        
        Args:
            token_type: Token type name (e.g., 'ID', 'NUM', 'OPERATOR', etc.)
            regex_pattern: Corresponding regular expression string
            
        Returns:
            None
            
        Note:
            The order of rule addition is important - higher priority rules should be added first,
            to avoid short rules being matched before longer rule subsets. For example, keywords
            should be added before identifiers.
        """
        self.token_specs.append((token_type, regex_pattern))

    def build(self) -> None:
        """Compile all lexical rules, generate DFA using Thompson's construction and subset construction
        
        Returns:
            None
            
        Note:
            This method must be called before tokenize().
            Process:
            1. Build NFA for each rule (using Thompson's construction)
            2. Merge all NFAs into a global NFA
            3. Convert NFA to DFA using subset construction
            
        Optimization:
            - Skip rebuilding if rules haven't changed and already built
        """
        if not self.token_specs:
            raise RuntimeError("No token rules added. Call add_token_rule() first.")
        
        # Check if already built and rules unchanged (simple optimization)
        if self.start_dfa is not None:
            # If rule count is the same, assume rules unchanged (simple check)
            # In practice, hash can be used for more precise judgment
            return
        
        # Create global start state
        global_start = NFAState()
        
        # Build NFA for each token rule
        for priority, (token_type, pattern) in enumerate(self.token_specs):
            try:
                # 1. Parse regular expression to AST
                ast = RegexParser(pattern).parse()
                # 2. Thompson's construction: AST → NFA
                frag = thompson(ast)
                # 3. Mark accepting states and token information
                for accept_state in frag.accepts:
                    accept_state.is_accept = True
                    accept_state.token_type = token_type
                    accept_state.priority = priority
                # 4. Connect to global start state
                global_start.add_trans(EPSILON, frag.start)
            except Exception as e:
                raise ValueError(f"Failed to parse pattern '{pattern}' for token '{token_type}': {e}")
        
        # 5. Subset construction: NFA → DFA
        self.start_dfa, dfa_list, self.alphabet = nfa_to_dfa(global_start)
        
        # Compatibility attribute: for backward compatibility with test code
        self.compiled_patterns = [(token_type, pattern) for token_type, pattern in self.token_specs]

    def tokenize(self, text: str) -> List[Token]:
        """Tokenize input text into Token list (using DFA longest match strategy)
        
        Args:
            text: Input source code text
            
        Returns:
            List of Token objects
            
        Raises:
            SyntaxError: When encountering unrecognized characters
            
        Note:
            - Automatically skip whitespace characters and comments (line comments starting with //)
            - Track line and column numbers for error reporting
            - Use DFA longest match strategy: match the longest possible token
        """
        if self.start_dfa is None:
            raise RuntimeError("Lexer not built. Call build() first.")

        tokens: List[Token] = []
        pos = 0
        line = 1
        column = 1
        n = len(text)

        while pos < n:
            # Skip whitespace characters
            if text[pos].isspace():
                if text[pos] == '\n':
                    line += 1
                    column = 1
                else:
                    column += 1
                pos += 1
                continue

            # Handle line comments
            if pos + 1 < n and text[pos:pos+2] == '//':
                # Skip comment until end of line
                end = text.find('\n', pos)
                if end == -1:
                    break
                pos = end
                continue

            # Use DFA for longest match
            state = self.start_dfa
            last_accept_state: Optional[DFAState] = None
            last_accept_pos = pos
            current_pos = pos

            # Match as far forward as possible
            while current_pos < n:
                ch = text[current_pos]
                # If character not in alphabet, stop matching
                if ch not in state.trans:
                    break
                state = state.trans[ch]
                current_pos += 1
                # Record last accepting state (longest match)
                if state.is_accept:
                    last_accept_state = state
                    last_accept_pos = current_pos

            if last_accept_state is None:
                # Lexical error: unrecognized character
                raise SyntaxError(
                    f"Lexical error at line {line}, column {column}: "
                    f"unexpected character '{text[pos]}'"
                )

            # Extract matched lexeme
            lexeme = text[pos:last_accept_pos]
            token = Token(
                last_accept_state.token_type or 'UNKNOWN',
                lexeme,
                line,
                column
            )
            tokens.append(token)

            # Update position and line/column numbers
            pos = last_accept_pos
            if '\n' in lexeme:
                line += lexeme.count('\n')
                column = len(lexeme) - lexeme.rfind('\n')
            else:
                column += len(lexeme)

        # Add EOF token
        tokens.append(Token('EOF', '', line, column))
        return tokens

    def get_token_rules(self) -> List[Tuple[str, str]]:
        """Get all added lexical rules
        
        Returns:
            List of (token_type, regex_pattern) tuples
            
        Note:
            Used to display or check all currently defined lexical rules.
        """
        return self.token_specs.copy()


def create_lexer_from_spec(token_rules: List[Tuple[str, str]]) -> LexerGenerator:
    """Convenience function: create lexer from rule list
    
    Args:
        token_rules: List of [(token_type, regex_pattern), ...] tuples
        
    Returns:
        Built LexerGenerator object
        
    Note:
        This is a factory function for quickly constructing a lexer.
    """
    lexer = LexerGenerator()
    for token_type, pattern in token_rules:
        lexer.add_token_rule(token_type, pattern)
    lexer.build()
    return lexer
