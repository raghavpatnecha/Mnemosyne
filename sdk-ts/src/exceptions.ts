/**
 * Exception classes for Mnemosyne SDK
 */

/**
 * Base exception for all Mnemosyne SDK errors
 */
export class MnemosyneError extends Error {
  constructor(
    message: string,
    public statusCode?: number
  ) {
    super(message);
    this.name = 'MnemosyneError';
    Object.setPrototypeOf(this, MnemosyneError.prototype);
  }
}

/**
 * Raised when API key is invalid or missing (401)
 */
export class AuthenticationError extends MnemosyneError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

/**
 * Raised when user lacks permission for resource (403)
 */
export class PermissionError extends MnemosyneError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'PermissionError';
    Object.setPrototypeOf(this, PermissionError.prototype);
  }
}

/**
 * Raised when resource is not found (404)
 */
export class NotFoundError extends MnemosyneError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'NotFoundError';
    Object.setPrototypeOf(this, NotFoundError.prototype);
  }
}

/**
 * Raised when request validation fails (422)
 */
export class ValidationError extends MnemosyneError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

/**
 * Raised when rate limit is exceeded (429)
 */
export class RateLimitError extends MnemosyneError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'RateLimitError';
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}

/**
 * Raised for server errors (5xx) or unknown errors
 */
export class APIError extends MnemosyneError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = 'APIError';
    Object.setPrototypeOf(this, APIError.prototype);
  }
}
