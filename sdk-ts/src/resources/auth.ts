/**
 * Auth resource implementation
 */

import { BaseClient } from '../base-client.js';
import type { RegisterRequest, RegisterResponse } from '../types/auth.js';

/**
 * Auth resource for user registration
 */
export class AuthResource {
  constructor(private client: BaseClient) {}

  /**
   * Register a new user and receive API key.
   *
   * **IMPORTANT**: The API key is only returned once. Save it securely!
   *
   * @param email - User email address
   * @param password - Password (minimum 8 characters)
   * @returns User ID, email, and API key
   * @throws {ValidationError} Invalid email or password too short
   * @throws {APIError} Email already registered (400) or server error
   *
   * @example
   * ```typescript
   * // Note: Don't need API key for registration
   * const client = new MnemosyneClient({ apiKey: 'not_needed' });
   * const response = await client.auth.register(
   *   'user@example.com',
   *   'secure_password_123'
   * );
   * console.log(`API Key: ${response.api_key}`);
   * // Save this API key securely!
   * ```
   */
  async register(email: string, password: string): Promise<RegisterResponse> {
    const data: RegisterRequest = { email, password };

    // Skip authentication for registration endpoint
    return this.client.request<RegisterResponse>('POST', 'auth/register', { json: data }, true);
  }
}
