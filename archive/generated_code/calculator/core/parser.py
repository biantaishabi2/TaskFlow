#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class ExpressionParser:
    """
    表达式解析器，负责将数学表达式解析为可执行的格式
    支持基本算术运算和括号解析
    """
    
    def __init__(self):
        self.position = 0
        self.expression = ""
        
    def parse(self, expression):
        """
        解析数学表达式
        
        Args:
            expression (str): 要解析的数学表达式
            
        Returns:
            值: 解析结果
        """
        self.position = 0
        self.expression = expression.replace(" ", "")  # 移除所有空格
        return self._parse_expression()
        
    def _parse_expression(self):
        """解析加减法表达式"""
        left = self._parse_term()
        
        while self.position < len(self.expression) and self.expression[self.position] in "+-":
            op = self.expression[self.position]
            self.position += 1
            right = self._parse_term()
            
            if op == '+':
                left += right
            else:
                left -= right
                
        return left
    
    def _parse_term(self):
        """解析乘除法表达式"""
        left = self._parse_factor()
        
        while (self.position < len(self.expression) and 
               self.expression[self.position] in "*/"):
            op = self.expression[self.position]
            self.position += 1
            right = self._parse_factor()
            
            if op == '*':
                left *= right
            else:
                if right == 0:
                    raise ZeroDivisionError("除数不能为零")
                left /= right
                
        return left
    
    def _parse_factor(self):
        """解析括号和数字"""
        # 处理括号
        if (self.position < len(self.expression) and 
            self.expression[self.position] == '('):
            self.position += 1
            result = self._parse_expression()
            
            if (self.position >= len(self.expression) or 
                self.expression[self.position] != ')'):
                raise SyntaxError("括号不匹配")
                
            self.position += 1
            return result
        
        # 处理负数
        if (self.position < len(self.expression) and 
            self.expression[self.position] == '-'):
            self.position += 1
            return -self._parse_factor()
        
        # 解析数字
        start = self.position
        while (self.position < len(self.expression) and 
               (self.expression[self.position].isdigit() or 
                self.expression[self.position] == '.')):
            self.position += 1
            
        if start == self.position:
            raise SyntaxError(f"无效的表达式在位置 {start}")
            
        try:
            return float(self.expression[start:self.position])
        except ValueError:
            raise SyntaxError(f"无效的数字: {self.expression[start:self.position]}")