/**
 * Type definitions for Auth API
 */

/**
 * Request schema for user registration
 */
export interface RegisterRequest {
  email: string;
  password: string;
}

/**
 * Response schema for user registration
 */
export interface RegisterResponse {
  user_id: string;
  email: string;
  api_key: string;
}
