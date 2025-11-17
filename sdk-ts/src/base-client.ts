/**
 * Base client implementation with shared logic for HTTP requests and error handling
 */

import {
  AuthenticationError,
  PermissionError,
  NotFoundError,
  ValidationError,
  RateLimitError,
  APIError,
} from './exceptions.js';

/**
 * Configuration options for the base client
 */
export interface BaseClientConfig {
  /** Mnemosyne API key (required, or set MNEMOSYNE_API_KEY env var) */
  apiKey?: string;
  /** Base URL for API (default: http://localhost:8000). Note: Must include /api/v1 suffix for API routes */
  baseUrl?: string;
  /** Request timeout in milliseconds (default: 60000 = 60 seconds) */
  timeout?: number;
  /** Maximum number of retries for failed requests (default: 3) */
  maxRetries?: number;
}

/**
 * Request options for HTTP requests
 */
interface RequestOptions {
  json?: unknown;
  params?: Record<string, string | number | boolean>;
  headers?: Record<string, string>;
}

/**
 * Base client with shared logic for HTTP requests and error handling.
 *
 * Provides:
 * - HTTP client management with native fetch
 * - Authentication headers
 * - Error handling and exception mapping
 * - Retry logic with exponential backoff
 */
export class BaseClient {
  /** @internal API key for authentication */
  public readonly apiKey: string;
  /** @internal Base URL for API requests */
  public readonly baseUrl: string;
  /** @internal Request timeout in milliseconds */
  public readonly timeout: number;
  /** @internal Maximum retry attempts */
  public readonly maxRetries: number;

  constructor(config: BaseClientConfig = {}) {
    // Get API key from config or environment
    this.apiKey = config.apiKey || process.env.MNEMOSYNE_API_KEY || '';

    if (!this.apiKey) {
      throw new Error(
        'API key is required. Provide it in config or set MNEMOSYNE_API_KEY environment variable.'
      );
    }

    // Get base URL from config or environment
    // Note: User must include /api/v1 in the base URL (matching Python SDK behavior)
    const rawBaseUrl =
      config.baseUrl || process.env.MNEMOSYNE_BASE_URL || 'http://localhost:8000';

    // Ensure baseUrl ends with / for correct URL resolution
    this.baseUrl = rawBaseUrl.endsWith('/') ? rawBaseUrl : `${rawBaseUrl}/`;

    this.timeout = config.timeout || 60000; // 60 seconds default
    this.maxRetries = config.maxRetries || 3;
  }

  /**
   * Get authentication headers for requests
   */
  protected getHeaders(skipAuth = false): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (!skipAuth) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    return headers;
  }

  /**
   * Handle error responses and raise appropriate exceptions
   */
  protected handleError(response: Response): void {
    if (response.ok) {
      return;
    }

    const statusCode = response.status;
    let message = `HTTP ${statusCode} error`;

    // Try to extract error message from response
    try {
      // Note: This is async, but we'll handle it synchronously for now
      // In real usage, caller should await response.json() before calling this
      message = response.statusText || message;
    } catch {
      // Use default message
    }

    // Map status codes to exception types
    switch (statusCode) {
      case 401:
        throw new AuthenticationError(message, statusCode);
      case 403:
        throw new PermissionError(message, statusCode);
      case 404:
        throw new NotFoundError(message, statusCode);
      case 422:
        throw new ValidationError(message, statusCode);
      case 429:
        throw new RateLimitError(message, statusCode);
      default:
        throw new APIError(message, statusCode);
    }
  }

  /**
   * Handle error responses asynchronously with proper error message extraction
   * @internal
   */
  public async handleErrorAsync(response: Response): Promise<void> {
    if (response.ok) {
      return;
    }

    const statusCode = response.status;
    let message = `HTTP ${statusCode} error`;

    // Try to extract error message from response
    try {
      const errorData = (await response.json()) as { detail?: string };
      message = errorData.detail || response.statusText || message;
    } catch {
      message = response.statusText || message;
    }

    // Map status codes to exception types
    switch (statusCode) {
      case 401:
        throw new AuthenticationError(message, statusCode);
      case 403:
        throw new PermissionError(message, statusCode);
      case 404:
        throw new NotFoundError(message, statusCode);
      case 422:
        throw new ValidationError(message, statusCode);
      case 429:
        throw new RateLimitError(message, statusCode);
      default:
        throw new APIError(message, statusCode);
    }
  }

  /**
   * Determine if a request should be retried
   */
  protected shouldRetry(response: Response | null, error: Error | null): boolean {
    // Retry on network errors
    if (error) {
      return true;
    }

    // Retry on 5xx server errors and 429 rate limits
    if (response && (response.status === 429 || response.status >= 500)) {
      return true;
    }

    return false;
  }

  /**
   * Calculate exponential backoff delay in milliseconds
   * @returns Delay in milliseconds (2^attempt seconds, max 16 seconds)
   */
  protected calculateBackoff(attempt: number): number {
    return Math.min(Math.pow(2, attempt) * 1000, 16000); // Max 16 seconds (16000ms)
  }

  /**
   * Make an HTTP request with retry logic
   */
  async request<T>(
    method: string,
    path: string,
    options: RequestOptions = {},
    skipAuth = false
  ): Promise<T> {
    const url = new URL(path, this.baseUrl);

    // Add query parameters
    if (options.params) {
      for (const [key, value] of Object.entries(options.params)) {
        url.searchParams.append(key, String(value));
      }
    }

    // Prepare headers
    const headers = {
      ...this.getHeaders(skipAuth),
      ...options.headers,
    };

    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(url.toString(), {
          method,
          headers,
          body: options.json ? JSON.stringify(options.json) : undefined,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        // Check if we should retry
        if (this.shouldRetry(response, null) && attempt < this.maxRetries - 1) {
          const delay = this.calculateBackoff(attempt);
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }

        // Handle errors (raises exceptions)
        await this.handleErrorAsync(response);

        // Parse and return response
        return (await response.json()) as T;
      } catch (error) {
        lastError = error as Error;

        // If it's an HTTP error, don't retry
        if (
          error instanceof AuthenticationError ||
          error instanceof PermissionError ||
          error instanceof NotFoundError ||
          error instanceof ValidationError
        ) {
          throw error;
        }

        // Retry on network errors
        if (attempt < this.maxRetries - 1) {
          const delay = this.calculateBackoff(attempt);
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }
      }
    }

    // All retries exhausted
    throw new APIError(
      `Request failed after ${this.maxRetries} retries: ${lastError?.message || 'Unknown error'}`
    );
  }

  /**
   * Make a streaming request (returns Response for SSE processing)
   */
  async requestStream(
    method: string,
    path: string,
    options: RequestOptions = {},
    skipAuth = false
  ): Promise<Response> {
    const url = new URL(path, this.baseUrl);

    // Add query parameters
    if (options.params) {
      for (const [key, value] of Object.entries(options.params)) {
        url.searchParams.append(key, String(value));
      }
    }

    // Prepare headers for SSE
    const headers = {
      ...this.getHeaders(skipAuth),
      Accept: 'text/event-stream',
      ...options.headers,
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    const response = await fetch(url.toString(), {
      method,
      headers,
      body: options.json ? JSON.stringify(options.json) : undefined,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle errors
    await this.handleErrorAsync(response);

    return response;
  }
}
