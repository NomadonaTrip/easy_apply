import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getRoles, createRole, deleteRole } from './roles';

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('roles API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getRoles', () => {
    it('should fetch roles from /api/v1/roles', async () => {
      const mockRoles = [
        { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' },
        { id: 2, user_id: 1, name: 'Business Analyst', created_at: '2026-01-02' },
      ];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockRoles),
      });

      const result = await getRoles();

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/roles',
        expect.objectContaining({
          credentials: 'include',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result).toEqual(mockRoles);
    });

    it('should throw error on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Unauthorized' }),
      });

      await expect(getRoles()).rejects.toThrow('Unauthorized');
    });
  });

  describe('createRole', () => {
    it('should POST to /api/v1/roles with role data', async () => {
      const newRole = { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve(newRole),
      });

      const result = await createRole({ name: 'Product Manager' });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/roles',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          body: JSON.stringify({ name: 'Product Manager' }),
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result).toEqual(newRole);
    });

    it('should throw error on validation failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve({
          detail: [{ msg: 'name cannot be empty', type: 'value_error', loc: ['body', 'name'] }],
        }),
      });

      await expect(createRole({ name: '' })).rejects.toThrow('name cannot be empty');
    });
  });

  describe('deleteRole', () => {
    it('should DELETE to /api/v1/roles/:id', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await deleteRole(1);

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/roles/1',
        expect.objectContaining({
          method: 'DELETE',
          credentials: 'include',
        })
      );
    });

    it('should throw error when role not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Role not found' }),
      });

      await expect(deleteRole(999)).rejects.toThrow('Role not found');
    });
  });
});
