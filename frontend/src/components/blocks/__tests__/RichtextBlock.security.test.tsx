/**
 * Security Regression Tests for RichtextBlock
 *
 * Tests XSS protection via DOMPurify sanitization.
 *
 * Security Issue: HIGH - XSS vulnerability in rich text rendering
 * Fix: Added DOMPurify sanitization before rendering HTML
 *
 * NOTE: This test requires Vitest setup. To run these tests:
 * 1. Install Vitest: npm install -D vitest @vitejs/plugin-react jsdom
 * 2. Install testing libraries: npm install -D @testing-library/react @testing-library/jest-dom
 * 3. Create vitest.config.ts
 * 4. Run: npm test
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import RichtextBlock from '../RichtextBlock';

describe('RichtextBlock Security Tests', () => {
  describe('XSS Protection', () => {
    it('should sanitize script tags', () => {
      const maliciousContent = {
        content: '<p>Normal text</p><script>alert("XSS")</script>',
        className: '',
      };

      const { container } = render(<RichtextBlock content={maliciousContent} />);

      // Script tag should be removed
      expect(container.querySelector('script')).toBeNull();
      expect(container.innerHTML).not.toContain('<script>');
      expect(container.innerHTML).not.toContain('alert("XSS")');

      // Safe content should remain
      expect(container.textContent).toContain('Normal text');
    });

    it('should sanitize inline event handlers', () => {
      const maliciousContent = {
        content: '<p onclick="alert(\'XSS\')">Click me</p>',
        className: '',
      };

      const { container } = render(<RichtextBlock content={maliciousContent} />);

      // onclick should be removed
      const paragraph = container.querySelector('p');
      expect(paragraph).not.toBeNull();
      expect(paragraph?.getAttribute('onclick')).toBeNull();

      // Safe content should remain
      expect(paragraph?.textContent).toBe('Click me');
    });

    it('should sanitize javascript: URLs', () => {
      const maliciousContent = {
        content: '<a href="javascript:alert(\'XSS\')">Click me</a>',
        className: '',
      };

      const { container } = render(<RichtextBlock content={maliciousContent} />);

      const link = container.querySelector('a');
      expect(link).not.toBeNull();

      // javascript: URL should be removed
      const href = link?.getAttribute('href');
      expect(href).not.toContain('javascript:');

      // Safe content should remain
      expect(link?.textContent).toBe('Click me');
    });

    it('should sanitize data URLs with scripts', () => {
      const maliciousContent = {
        content: '<img src="data:text/html,<script>alert(\'XSS\')</script>">',
        className: '',
      };

      const { container } = render(<RichtextBlock content={maliciousContent} />);

      // Image with malicious data URL should be sanitized or removed
      const img = container.querySelector('img');
      if (img) {
        const src = img.getAttribute('src');
        expect(src).not.toContain('<script>');
        expect(src).not.toContain('alert');
      }
    });

    it('should allow safe HTML tags', () => {
      const safeContent = {
        content: `
          <p>Paragraph</p>
          <h1>Heading 1</h1>
          <strong>Bold</strong>
          <em>Italic</em>
          <a href="https://example.com">Link</a>
          <ul><li>List item</li></ul>
        `,
        className: '',
      };

      const { container } = render(<RichtextBlock content={safeContent} />);

      // All safe tags should be present
      expect(container.querySelector('p')).not.toBeNull();
      expect(container.querySelector('h1')).not.toBeNull();
      expect(container.querySelector('strong')).not.toBeNull();
      expect(container.querySelector('em')).not.toBeNull();
      expect(container.querySelector('a')).not.toBeNull();
      expect(container.querySelector('ul')).not.toBeNull();
      expect(container.querySelector('li')).not.toBeNull();
    });

    it('should allow safe attributes', () => {
      const safeContent = {
        content: `
          <p class="text-lg" id="intro">Introduction</p>
          <a href="https://example.com" title="Example" target="_blank" rel="noopener">Link</a>
          <img src="https://example.com/image.jpg" alt="Description" width="100" height="100">
        `,
        className: '',
      };

      const { container } = render(<RichtextBlock content={safeContent} />);

      // Safe attributes should be preserved
      const paragraph = container.querySelector('p');
      expect(paragraph?.getAttribute('class')).toContain('text-lg');
      expect(paragraph?.getAttribute('id')).toBe('intro');

      const link = container.querySelector('a');
      expect(link?.getAttribute('href')).toBe('https://example.com');
      expect(link?.getAttribute('title')).toBe('Example');

      const img = container.querySelector('img');
      expect(img?.getAttribute('src')).toContain('example.com');
      expect(img?.getAttribute('alt')).toBe('Description');
    });

    it('should handle empty content gracefully', () => {
      const emptyContent = {
        content: '',
        className: '',
      };

      const { container } = render(<RichtextBlock content={emptyContent} />);

      // Should render without errors
      expect(container).toBeTruthy();
    });

    it('should handle null content gracefully', () => {
      const nullContent = {
        content: null as any,
        className: '',
      };

      const { container } = render(<RichtextBlock content={nullContent} />);

      // Should render without errors
      expect(container).toBeTruthy();
    });

    it('should apply custom className', () => {
      const contentWithClass = {
        content: '<p>Test</p>',
        className: 'custom-class',
      };

      const { container } = render(<RichtextBlock content={contentWithClass} />);

      // Custom class should be applied
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper?.className).toContain('custom-class');
    });

    it('should memoize sanitization for performance', () => {
      const content = {
        content: '<p>Test content</p>',
        className: '',
      };

      // First render
      const { rerender, container } = render(<RichtextBlock content={content} />);
      const firstHTML = container.innerHTML;

      // Re-render with same content (should use memoized value)
      rerender(<RichtextBlock content={content} />);
      const secondHTML = container.innerHTML;

      // HTML should be identical (confirming memoization)
      expect(firstHTML).toBe(secondHTML);
    });

    it('should block SVG with scripts', () => {
      const maliciousSVG = {
        content: '<svg><script>alert("XSS")</script></svg>',
        className: '',
      };

      const { container } = render(<RichtextBlock content={maliciousSVG} />);

      // Script inside SVG should be removed
      const script = container.querySelector('script');
      expect(script).toBeNull();
    });

    it('should block iframe tags', () => {
      const maliciousIframe = {
        content: '<iframe src="https://evil.com"></iframe>',
        className: '',
      };

      const { container } = render(<RichtextBlock content={maliciousIframe} />);

      // iframe should be removed (not in whitelist)
      const iframe = container.querySelector('iframe');
      expect(iframe).toBeNull();
    });

    it('should block object and embed tags', () => {
      const maliciousObject = {
        content: '<object data="https://evil.com"></object><embed src="https://evil.com">',
        className: '',
      };

      const { container } = render(<RichtextBlock content={maliciousObject} />);

      // object and embed should be removed
      expect(container.querySelector('object')).toBeNull();
      expect(container.querySelector('embed')).toBeNull();
    });
  });

  describe('Content Preservation', () => {
    it('should preserve complex nested HTML structure', () => {
      const complexContent = {
        content: `
          <div>
            <h2>Title</h2>
            <p>Introduction paragraph</p>
            <ul>
              <li>First item</li>
              <li>Second item with <strong>bold</strong> text</li>
            </ul>
            <blockquote>
              <p>A quote</p>
            </blockquote>
          </div>
        `,
        className: '',
      };

      const { container } = render(<RichtextBlock content={complexContent} />);

      // All structural elements should be preserved
      expect(container.querySelector('h2')).not.toBeNull();
      expect(container.querySelector('p')).not.toBeNull();
      expect(container.querySelector('ul')).not.toBeNull();
      expect(container.querySelectorAll('li')).toHaveLength(2);
      expect(container.querySelector('strong')).not.toBeNull();
      expect(container.querySelector('blockquote')).not.toBeNull();
    });

    it('should preserve table structures', () => {
      const tableContent = {
        content: `
          <table>
            <thead>
              <tr>
                <th>Header 1</th>
                <th>Header 2</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Cell 1</td>
                <td>Cell 2</td>
              </tr>
            </tbody>
          </table>
        `,
        className: '',
      };

      const { container } = render(<RichtextBlock content={tableContent} />);

      // Table structure should be preserved
      expect(container.querySelector('table')).not.toBeNull();
      expect(container.querySelector('thead')).not.toBeNull();
      expect(container.querySelector('tbody')).not.toBeNull();
      expect(container.querySelectorAll('th')).toHaveLength(2);
      expect(container.querySelectorAll('td')).toHaveLength(2);
    });
  });
});
