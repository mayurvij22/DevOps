package com.mayur.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class AppTest {

    @Test
    void addsTwoNumbers() {
        // Break-it lab: change 5 to 6, push, and watch the pipeline fail.
        assertEquals(5, App.add(2, 3));
    }
}
