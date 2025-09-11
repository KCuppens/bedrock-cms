"""
Security audit utilities for verifying permission enforcement.
"""

import logging
from typing import Dict, List, Any
from django.urls import get_resolver
from django.conf import settings
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class SecurityAuditReport:
    """
    Generate security audit reports for API endpoints.
    """
    
    def __init__(self):
        self.endpoints = []
        self.issues = []
        self.warnings = []
    
    def audit_all_endpoints(self) -> Dict[str, Any]:
        """
        Audit all API endpoints for security issues.
        
        Returns:
            Dict containing audit results
        """
        # Get all URL patterns
        resolver = get_resolver()
        self._audit_url_patterns(resolver.url_patterns, '')
        
        return {
            'total_endpoints': len(self.endpoints),
            'issues_found': len(self.issues),
            'warnings_found': len(self.warnings),
            'endpoints': self.endpoints,
            'issues': self.issues,
            'warnings': self.warnings,
            'summary': self._generate_summary()
        }
    
    def _audit_url_patterns(self, patterns, prefix=''):
        """Recursively audit URL patterns."""
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):
                # Include pattern for nested URLs
                self._audit_url_patterns(
                    pattern.url_patterns, 
                    prefix + str(pattern.pattern)
                )
            elif hasattr(pattern, 'callback'):
                # This is an endpoint
                endpoint_info = self._audit_endpoint(pattern, prefix)
                if endpoint_info:
                    self.endpoints.append(endpoint_info)
    
    def _audit_endpoint(self, pattern, prefix):
        """Audit a single endpoint."""
        callback = pattern.callback
        
        # Skip non-API endpoints
        if not self._is_api_endpoint(pattern, prefix):
            return None
        
        path = prefix + str(pattern.pattern)
        
        endpoint_info = {
            'path': path,
            'name': getattr(pattern, 'name', 'unknown'),
            'view_class': None,
            'permission_classes': [],
            'throttle_classes': [],
            'authentication_classes': [],
            'has_csrf_protection': False,
            'security_score': 0,
            'issues': [],
            'warnings': []
        }
        
        # Get view class information
        if hasattr(callback, 'cls'):
            view_class = callback.cls
            endpoint_info['view_class'] = view_class.__name__
            
            # Check permission classes
            if hasattr(view_class, 'permission_classes'):
                endpoint_info['permission_classes'] = [
                    cls.__name__ for cls in view_class.permission_classes
                ]
            
            # Check throttle classes
            if hasattr(view_class, 'throttle_classes'):
                endpoint_info['throttle_classes'] = [
                    cls.__name__ for cls in view_class.throttle_classes
                ]
            
            # Check authentication classes
            if hasattr(view_class, 'authentication_classes'):
                endpoint_info['authentication_classes'] = [
                    cls.__name__ for cls in view_class.authentication_classes
                ]
            
            # Audit the endpoint for security issues
            self._audit_endpoint_security(endpoint_info, view_class)
        
        return endpoint_info
    
    def _is_api_endpoint(self, pattern, prefix):
        """Check if this is an API endpoint we should audit."""
        path = prefix + str(pattern.pattern)
        
        # Check for API paths
        api_indicators = ['/api/', '/v1/', 'api/v1/', 'reports/', 'media/', 'cms/', 'i18n/']
        
        return any(indicator in path for indicator in api_indicators)
    
    def _audit_endpoint_security(self, endpoint_info, view_class):
        """Audit security aspects of an endpoint."""
        issues = []
        warnings = []
        score = 0
        
        # Check for authentication
        auth_classes = endpoint_info['authentication_classes']
        perm_classes = endpoint_info['permission_classes']
        
        if not auth_classes:
            # Check if using default authentication from settings
            if hasattr(settings, 'REST_FRAMEWORK') and 'DEFAULT_AUTHENTICATION_CLASSES' in settings.REST_FRAMEWORK:
                auth_classes = [
                    cls.split('.')[-1] for cls in 
                    settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']
                ]
                endpoint_info['authentication_classes'] = auth_classes
        
        # Authentication checks
        if not auth_classes:
            issues.append("No authentication classes configured")
        elif 'SessionAuthentication' in auth_classes:
            score += 20
            endpoint_info['has_csrf_protection'] = True
        
        # Permission checks
        if not perm_classes:
            # Check for default permissions
            if hasattr(settings, 'REST_FRAMEWORK') and 'DEFAULT_PERMISSION_CLASSES' in settings.REST_FRAMEWORK:
                perm_classes = [
                    cls.split('.')[-1] for cls in 
                    settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']
                ]
                endpoint_info['permission_classes'] = perm_classes
        
        if 'AllowAny' in perm_classes:
            warnings.append("Uses AllowAny permission - ensure this is intentional for public endpoints")
        elif 'IsAuthenticated' in perm_classes:
            score += 30
        elif 'DjangoModelPermissions' in perm_classes:
            score += 40  # Higher score for model-specific permissions
        
        # Throttling checks
        throttle_classes = endpoint_info['throttle_classes']
        if not throttle_classes:
            # Check for default throttling
            if hasattr(settings, 'REST_FRAMEWORK') and 'DEFAULT_THROTTLE_CLASSES' in settings.REST_FRAMEWORK:
                throttle_classes = [
                    cls.split('.')[-1] for cls in 
                    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']
                ]
                endpoint_info['throttle_classes'] = throttle_classes
        
        if throttle_classes:
            score += 20
        else:
            warnings.append("No rate limiting configured")
        
        # Check for write operation security
        if self._is_write_endpoint(view_class, endpoint_info['path']):
            if 'WriteOperationThrottle' not in endpoint_info['throttle_classes']:
                warnings.append("Write endpoint without write-specific throttling")
            
            if not endpoint_info['has_csrf_protection']:
                issues.append("Write endpoint without CSRF protection")
            else:
                score += 20
        
        # Check for admin-only endpoints
        if self._is_admin_endpoint(endpoint_info['path']):
            if 'IsAdminUser' not in perm_classes and 'DjangoModelPermissions' not in perm_classes:
                issues.append("Admin endpoint without admin permissions")
            else:
                score += 10
        
        # Check for media upload endpoints
        if 'media' in endpoint_info['path'] and 'POST' in endpoint_info.get('methods', ['POST']):
            if 'MediaUploadThrottle' not in endpoint_info['throttle_classes']:
                warnings.append("Media upload endpoint without upload throttling")
        
        # Store results
        endpoint_info['issues'] = issues
        endpoint_info['warnings'] = warnings
        endpoint_info['security_score'] = min(100, score)  # Cap at 100
        
        # Add to global lists
        self.issues.extend([
            {'endpoint': endpoint_info['path'], 'issue': issue} 
            for issue in issues
        ])
        self.warnings.extend([
            {'endpoint': endpoint_info['path'], 'warning': warning} 
            for warning in warnings
        ])
    
    def _is_write_endpoint(self, view_class, path):
        """Check if this is a write endpoint."""
        # Check if it's a ViewSet with write methods
        if issubclass(view_class, (ModelViewSet, ViewSet)):
            return True
        
        # Check path patterns that suggest write operations
        write_patterns = ['create', 'update', 'delete', 'publish', 'upload', 'replace']
        return any(pattern in path.lower() for pattern in write_patterns)
    
    def _is_admin_endpoint(self, path):
        """Check if this is an admin-only endpoint."""
        admin_patterns = ['/admin', 'reports/', 'audit/', 'task-status']
        return any(pattern in path.lower() for pattern in admin_patterns)
    
    def _generate_summary(self):
        """Generate audit summary."""
        total_endpoints = len(self.endpoints)
        
        if total_endpoints == 0:
            return {"message": "No endpoints found"}
        
        # Calculate average security score
        scores = [ep['security_score'] for ep in self.endpoints]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Count endpoints by security level
        high_security = len([s for s in scores if s >= 80])
        medium_security = len([s for s in scores if 50 <= s < 80])
        low_security = len([s for s in scores if s < 50])
        
        # Count common issues
        issue_types = {}
        for issue in self.issues:
            issue_type = issue['issue']
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        return {
            'average_security_score': round(avg_score, 2),
            'endpoints_by_security': {
                'high_security': high_security,
                'medium_security': medium_security,
                'low_security': low_security
            },
            'common_issues': issue_types,
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self):
        """Generate security recommendations based on audit results."""
        recommendations = []
        
        # Check for common issues
        unauth_count = len([i for i in self.issues if 'authentication' in i['issue'].lower()])
        csrf_count = len([i for i in self.issues if 'csrf' in i['issue'].lower()])
        throttle_count = len([w for w in self.warnings if 'throttling' in w['warning'].lower()])
        
        if unauth_count > 0:
            recommendations.append("Configure authentication for all API endpoints")
        
        if csrf_count > 0:
            recommendations.append("Ensure CSRF protection is enabled for write operations")
        
        if throttle_count > 3:
            recommendations.append("Add rate limiting to prevent abuse")
        
        if len(self.issues) == 0:
            recommendations.append("Security audit passed - continue monitoring")
        
        return recommendations


def run_security_audit():
    """
    Run a comprehensive security audit.
    
    Returns:
        Dict with audit results
    """
    auditor = SecurityAuditReport()
    return auditor.audit_all_endpoints()


def print_security_audit_report(report=None):
    """
    Print a formatted security audit report.
    
    Args:
        report: Audit report dict, if None will run new audit
    """
    if report is None:
        report = run_security_audit()
    
    print("=" * 60)
    print("SECURITY AUDIT REPORT")
    print("=" * 60)
    
    print(f"\nTotal Endpoints Audited: {report['total_endpoints']}")
    print(f"Security Issues Found: {report['issues_found']}")
    print(f"Warnings: {report['warnings_found']}")
    
    if 'summary' in report:
        summary = report['summary']
        print(f"\nAverage Security Score: {summary['average_security_score']}/100")
        
        security_dist = summary['endpoints_by_security']
        print(f"High Security (80+): {security_dist['high_security']}")
        print(f"Medium Security (50-79): {security_dist['medium_security']}")
        print(f"Low Security (<50): {security_dist['low_security']}")
    
    if report['issues_found'] > 0:
        print(f"\n🔴 CRITICAL ISSUES:")
        for issue in report['issues'][:10]:  # Show first 10
            print(f"  - {issue['endpoint']}: {issue['issue']}")
    
    if report['warnings_found'] > 0:
        print(f"\n🟡 WARNINGS:")
        for warning in report['warnings'][:10]:  # Show first 10
            print(f"  - {warning['endpoint']}: {warning['warning']}")
    
    if 'recommendations' in report.get('summary', {}):
        print(f"\n📋 RECOMMENDATIONS:")
        for rec in report['summary']['recommendations']:
            print(f"  - {rec}")
    
    print("\n" + "=" * 60)