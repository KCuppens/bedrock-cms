import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { NotFoundState } from '@/components/EmptyStates';
import { useEffect } from "react";

const NotFound = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname
    );
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <NotFoundState
        title="Page not found"
        description="The page you're looking for doesn't exist or has been moved."
        onGoBack={() => navigate(-1)}
      />
    </div>
  );
};

export default NotFound;
