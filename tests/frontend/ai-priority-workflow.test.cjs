
// RED tests for priority-aware AI textbox integration.
// Existing manual controls must continue using /api/repair.

const {test} = require('node:test');
const assert = require('node:assert/strict');
const {page, draft, confirm} = require('./helpers/page.cjs');


function aiReply(data, missing, primary = 'symmetry') {
  const routine = structuredClone(data.routine);

  for (const formation of routine.formations) {
    formation.dancers = formation.dancers.filter(
      p => p.id !== missing
    );
  }

  return {
    routine,
    valid: true,
    errors: [],
    changed_assignments: 0,
    total_displacement: 0,
    requirements: {
      primary_priority: primary,
      secondary_priorities: [],
      constraints: {}
    },
    alternatives: []
  };
}


test(
  'AI textbox sends original instructions and routine to /api/repair-ai',
  async () => {
    const p = page();
    const data = draft();

    await confirm(p, data);

    const requests = [];

    const instruction =
      'Prioritize symmetry, but move at most three dancers.';

    p.el('ai-instruction').value = instruction;
    p.el('missing').value = 'Rhea';

    p.context.fetch = async (url, options) => {
      requests.push({
        url,
        body: JSON.parse(options.body)
      });

      return {
        ok: true,
        json: async () => aiReply(data, 'Rhea')
      };
    };

    await p.el('ai-run').onclick();

    assert.deepEqual(
      requests.map(r => r.url),
      ['/api/repair-ai']
    );

    assert.equal(requests[0].body.instruction, instruction);
    assert.equal(requests[0].body.missing, 'Rhea');

    assert.deepEqual(
      requests[0].body.routine,
      data.routine
    );

    assert.match(
      p.el('ai-status').textContent,
      /symmetry/i
    );

    assert.equal(p.el('approve').disabled, false);
  }
);


test(
  'manual preferences still work through the original endpoint',
  async () => {
    const p = page();
    const data = draft();

    await confirm(p, data);

    const requests = [];

    p.context.fetch = async (url, options) => {
      const body = JSON.parse(options.body);

      requests.push({url, body});

      return {
        ok: true,
        json: async () => aiReply(data, body.missing)
      };
    };

    for (const preference of [
      'minimize_changes',
      'preserve_center'
    ]) {
      p.el('preference').value = preference;

      await p.el('run').onclick();

      assert.equal(
        requests.at(-1).url,
        '/api/repair'
      );

      assert.equal(
        requests.at(-1).body.preference,
        preference
      );
    }

    assert.equal(requests.length, 2);
  }
);


test(
  'unsupported AI requirement reports an error without disabling manual repair',
  async () => {
    const p = page();
    const data = draft();

    await confirm(p, data);

    p.el('ai-instruction').value = 'Make everyone fly';

    const urls = [];

    p.context.fetch = async url => {
      urls.push(url);

      return {
        ok: false,
        json: async () => ({
          detail: 'Unsupported AI requirement'
        })
      };
    };

    await p.el('ai-run').onclick();

    assert.deepEqual(
      urls,
      ['/api/repair-ai']
    );

    assert.match(
      p.el('ai-status').textContent,
      /unsupported/i
    );

    assert.equal(p.el('approve').disabled, true);
    assert.equal(p.el('run').disabled, false);
  }
);
